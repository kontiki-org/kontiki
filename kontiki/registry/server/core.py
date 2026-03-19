import logging
from collections import defaultdict
from datetime import datetime, timedelta
from enum import Enum

from aio_pika import connect_robust

from kontiki.delegate import ServiceDelegate
from kontiki.messaging.common import create_tls_context, get_amqp_url
from kontiki.messaging.serialization import Serializer
from kontiki.registry.common import declare_registry_admin_exchange
from kontiki.registry.server.delegates.event_tracking import EventTracker
from kontiki.registry.server.delegates.exception_tracking import ExceptionTracker
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

        self.event_tracker = EventTracker(self)
        self.registry = Registry(self)
        self.heartbeat_manager = HeartbeatManager(self)
        self.exception_tracker = ExceptionTracker(self)
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
        await self.event_tracker.setup()
        await self.registry.setup()
        await self.heartbeat_manager.setup()
        await self.exception_tracker.setup()

    async def stop(self):
        if self.connection:
            await self.connection.close()

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
        is_degraded = self.heartbeat_manager.is_degraded(service_name, instance_id)

        is_late = datetime.now() - last_heartbeat > timedelta(seconds=timeout)
        if not last_heartbeat or is_late:
            return ServiceStatus.DOWN.value
        if is_degraded:
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
                        filtered_services[service_name][instance_id] = {
                            "status": current_status,
                            "metadata": data,
                        }
        except Exception as e:
            logging.error("Error while getting services: (%s)", e)

        return dict(filtered_services)

    def get_events(self):
        return make_serializable(self.event_tracker.events)

    def get_exceptions(self):
        return make_serializable(self.exception_tracker.exceptions)
