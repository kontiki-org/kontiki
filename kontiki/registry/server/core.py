import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from enum import Enum

from aio_pika import connect_robust

from kontiki.delegate import ServiceDelegate
from kontiki.messaging.common import (
    create_tls_context,
    failed_queue_name,
    get_amqp_url,
)
from kontiki.messaging.serialization import Serializer
from kontiki.registry.common import declare_registry_admin_exchange
from kontiki.registry.events import (
    EXCEPTION_RECORDED,
    INSTANCE_DEREGISTERED,
    INSTANCE_REGISTERED,
    INSTANCE_STATUS_CHANGED,
    deregistered_payload,
    exception_recorded_payload,
    registered_payload,
    status_changed_payload,
)
from kontiki.registry.server.delegates.activity_tracking import ActivityTracker
from kontiki.registry.server.delegates.heartbeat_manager import HeartbeatManager
from kontiki.registry.server.delegates.registry import Registry

# -----------------------------------------------------------------------------


def make_serializable(obj):
    if isinstance(obj, dict):
        return {k: make_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [make_serializable(item) for item in obj]
    if isinstance(obj, set):
        return list(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    if hasattr(obj, "__dict__"):
        return make_serializable(obj.__dict__)
    if isinstance(obj, bytes):
        return obj.decode("utf-8", errors="replace")
    return obj


# -----------------------------------------------------------------------------


class ServiceStatus(Enum):
    ACTIVE = "active"
    DEGRADED = "degraded"
    DOWN = "down"


class ServiceRegistryCore(ServiceDelegate):
    def __init__(self):
        self.connection = None
        self.channel = None
        self.registry_admin_exchange = None

        self.heartbeats = {}
        self.default_timeout_factor = 3
        self._tracked_status = {}

        self.activity_tracker = ActivityTracker(self)
        self.registry = Registry(self)
        self.heartbeat_manager = HeartbeatManager(self)
        super().__init__()

    async def setup(self):
        logging.debug("ServiceRegistration Setup")
        amqp_url = get_amqp_url(self.container.config)

        ssl_ctx = create_tls_context(self.container.config)
        self.connection = await connect_robust(amqp_url, ssl_context=ssl_ctx)

        self.channel = await self.connection.channel()
        await self.channel.set_qos(prefetch_count=10)
        self.registry_admin_exchange = await declare_registry_admin_exchange(
            self.channel
        )

        # Sets serializer
        self.serializer = Serializer(self.container.config)

        # Sets delegates up.
        await self.activity_tracker.setup()
        await self.registry.setup()
        await self.heartbeat_manager.setup()

    async def stop(self):
        if self.connection:
            await self.connection.close()

    async def publish_registry_event(self, event_type, payload):
        await self.container.messenger.publish(event_type, payload)

    async def on_instance_registered(self, data):
        await self.publish_registry_event(INSTANCE_REGISTERED, registered_payload(data))
        self._tracked_status[
            (data["service_name"], data["instance_id"])
        ] = ServiceStatus.DOWN.value

    async def on_instance_deregistered(self, service_name, instance_id):
        await self.publish_registry_event(
            INSTANCE_DEREGISTERED,
            deregistered_payload(service_name, instance_id),
        )
        self._tracked_status.pop((service_name, instance_id), None)

    async def on_exception_recorded(self, exception_data):
        await self.publish_registry_event(
            EXCEPTION_RECORDED, exception_recorded_payload(exception_data)
        )

    async def refresh_instance_status(self, service_name, instance_id, reason=None):
        if not self.registry.has_service_instance(service_name, instance_id):
            return

        data = self.registry.services[service_name][instance_id]
        timeout = self._get_timeout(data.get("heartbeat_interval", 10))
        new_status = self._get_instance_status(instance_id, service_name, timeout)
        key = (service_name, instance_id)
        previous_status = self._tracked_status.get(key)
        if previous_status == new_status:
            return

        self._tracked_status[key] = new_status
        if previous_status is None:
            return

        await self.publish_registry_event(
            INSTANCE_STATUS_CHANGED,
            status_changed_payload(
                service_name,
                instance_id,
                previous_status,
                new_status,
                reason=reason,
            ),
        )

    async def refresh_all_instance_statuses(self):
        for service_name, instances in self.registry.services.items():
            for instance_id in list(instances.keys()):
                await self.refresh_instance_status(service_name, instance_id)

    async def create_and_consume_queue(self, routing_key, callback):
        queue_name = f"{routing_key}.queue"
        try:
            queue = await self.channel.declare_queue(queue_name, durable=True)
            await queue.bind(self.registry_admin_exchange, routing_key=routing_key)
            logging.debug("Binding %s with rkey %s", queue_name, routing_key)
            await queue.consume(callback)
            logging.debug("Created and bound queue: %s", queue_name)
        except Exception as e:
            logging.error("Error creating or consuming queue %s: %s", queue_name, e)

    def _get_instance_status(self, instance_id, service_name, timeout):
        logging.debug("Get %s-%s status.", service_name, instance_id)
        last_heartbeat = self.heartbeat_manager.get_last_heartbeat(
            service_name, instance_id
        )
        if not last_heartbeat:
            return ServiceStatus.DOWN.value
        is_late = datetime.now(timezone.utc) - last_heartbeat > timedelta(
            seconds=timeout
        )
        if is_late:
            return ServiceStatus.DOWN.value
        if self.heartbeat_manager.is_degraded(service_name, instance_id):
            return ServiceStatus.DEGRADED.value
        return ServiceStatus.ACTIVE.value

    def _get_timeout(self, heartbeat_interval):
        if heartbeat_interval is None:
            heartbeat_interval = 10
        timeout = heartbeat_interval * self.default_timeout_factor
        logging.debug("Calculated timeout = %s", timeout)
        return timeout

    def get_services(self, status=None):
        filtered_services = defaultdict(dict)
        try:
            for service_name, instances in self.registry.services.items():
                for instance_id, data in instances.items():
                    heartbeat_interval = data.get("heartbeat_interval", 10)
                    current_status = self._get_instance_status(
                        instance_id, service_name, self._get_timeout(heartbeat_interval)
                    )
                    if not status or current_status == status:
                        last_heartbeat = self.heartbeat_manager.get_last_heartbeat(
                            service_name, instance_id
                        )
                        if last_heartbeat:
                            last_heartbeat = last_heartbeat.isoformat()
                        degraded_reason = self.heartbeat_manager.get_degraded_reason(
                            service_name, instance_id
                        )
                        filtered_services[service_name][instance_id] = {
                            "status": current_status,
                            "last_heartbeat": last_heartbeat,
                            "degraded_reason": degraded_reason,
                            "metadata": data,
                        }
        except Exception as e:
            logging.error("Error while getting services: (%s)", e)

        return dict(filtered_services)

    def list_instances(self, service_name):
        if not isinstance(service_name, str) or not service_name.strip():
            return []
        instances = self.registry.services.get(service_name)
        if not instances:
            return []
        live = []
        for instance_id, data in instances.items():
            status = self._get_instance_status(
                instance_id,
                service_name,
                self._get_timeout(data.get("heartbeat_interval", 10)),
            )
            if status in (ServiceStatus.ACTIVE.value, ServiceStatus.DEGRADED.value):
                live.append(instance_id)
        live.sort()
        return live

    def declares_competing_event(self, service_name, event_name):
        instances = self.registry.services.get(service_name)
        if not instances:
            return False
        for instance_id, data in instances.items():
            status = self._get_instance_status(
                instance_id,
                service_name,
                self._get_timeout(data.get("heartbeat_interval", 10)),
            )
            if status not in (ServiceStatus.ACTIVE.value, ServiceStatus.DEGRADED.value):
                continue
            entrypoints = data.get("entrypoints")
            if not entrypoints:
                continue
            for entry in entrypoints:
                if (
                    entry.get("type") == "event"
                    and entry.get("name") == event_name
                    and entry.get("mode") == "competing"
                ):
                    return True
        return False

    async def list_failed_messages(self, service_name, event_name, limit):
        channel = await self.connection.channel()
        try:
            queue = await channel.declare_queue(
                failed_queue_name(service_name, event_name), passive=True
            )
            count = queue.declaration_result.message_count
            held = []
            messages = []
            for _ in range(limit):
                message = await queue.get(fail=False)
                if message is None:
                    break
                held.append(message)
                messages.append(json.loads(message.body))
            for message in held:
                await message.nack(requeue=True)
            return {"count": count, "messages": messages}
        finally:
            await channel.close()

    async def replay_failed_messages(self, service_name, event_name, count):
        channel = await self.connection.channel()
        try:
            queue = await channel.declare_queue(
                failed_queue_name(service_name, event_name), passive=True
            )
            replayed = 0
            for _ in range(count):
                message = await queue.get(fail=False)
                if message is None:
                    break
                await self.container.messenger.publish(
                    event_name, json.loads(message.body)
                )
                await message.ack()
                replayed += 1
            logging.info(
                "Replayed %s failed message(s) for %s %s.",
                replayed,
                service_name,
                event_name,
            )
            return {"replayed": replayed}
        finally:
            await channel.close()

    def is_live(self, service_name):
        if service_name == self.container.service_name:
            return True

        instances = self.registry.services.get(service_name)
        if not instances:
            return False

        for instance_id, data in instances.items():
            status = self._get_instance_status(
                instance_id,
                service_name,
                self._get_timeout(data.get("heartbeat_interval", 10)),
            )
            if status in (ServiceStatus.ACTIVE.value, ServiceStatus.DEGRADED.value):
                return True
        return False

    def get_events(self):
        return make_serializable(self.activity_tracker.events)

    def get_exceptions(self):
        return make_serializable(self.activity_tracker.exceptions)
