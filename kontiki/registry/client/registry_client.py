import asyncio
from datetime import datetime

from aio_pika import Message, connect_robust

from kontiki import __version__
from kontiki.configuration.parameter import get_kontiki_parameter
from kontiki.messaging.common import create_tls_context, get_amqp_url, is_amqp_required
from kontiki.messaging.serialization import Serializer
from kontiki.registry.common import (
    EXCEPTION_RKEY,
    HEARTBEAT_RKEY,
    REGISTER_RKEY,
    UNREGISTER_RKEY,
    declare_registry_admin_exchange,
    get_heartbeat_interval,
    get_registration_group,
)
from kontiki.utils import log

# -----------------------------------------------------------------------------


def publish(routing_key):
    def decorator(func):
        async def wrapper(self, *args, **kwargs):
            if not self.registry_admin_exchange:
                msg = "Registry Admin Exchange not setup."
                log.error(msg)
                raise RuntimeError(msg)

            body = await func(self, *args, **kwargs)

            message = Message(body=self.serializer.dumps(body))
            await self.registry_admin_exchange.publish(message, routing_key=routing_key)
            log.debug("Published message to %s: %s", routing_key, body)

        return wrapper

    return decorator


# -----------------------------------------------------------------------------


class ServiceRegistryClient:
    def __init__(self, container):
        self.container = container
        self.connection = None
        self.channel = None
        self.registry_admin_exchange = None
        self._register_again_queue = None
        self._register_again_consumer_tag = None
        self._registered = False

    async def setup(self):
        log.debug("ServiceRegistryClient Setup")
        amqp_url = get_amqp_url(self.container.config)
        ssl_ctx = create_tls_context(self.container.config)
        fail_fast = is_amqp_required(self.container.config)
        self.connection = await connect_robust(
            amqp_url, ssl_context=ssl_ctx, fail_fast=fail_fast
        )
        self.channel = await self.connection.channel()
        await self.channel.set_qos(prefetch_count=10)
        self.registry_admin_exchange = await declare_registry_admin_exchange(
            self.channel
        )
        self.serializer = Serializer(self.container.config)

        service_name = self.container.service_name
        instance_id = self.container.instance_id
        # Per-instance queue: a shared register_again.queue would let any
        # Kontiki process on the vhost consume another instance's signal.
        queue_name = f"{service_name}.{instance_id}.register_again.queue"
        self._register_again_queue = await self.channel.declare_queue(
            queue_name, durable=True
        )
        routing_key = f"{service_name}.{instance_id}.register_again"
        await self._register_again_queue.bind(
            self.registry_admin_exchange, routing_key=routing_key
        )
        self._register_again_consumer_tag = await self._register_again_queue.consume(
            self._register_again
        )
        self.connection.reconnect_callbacks.add(self._on_amqp_reconnect)

        if not self._registered:
            delay = get_kontiki_parameter(
                self.container.config, "registration.delay", default=2
            )
            log.info("Delaying registration by %s seconds.", delay)
            await asyncio.sleep(delay)
        await self.register()
        self._registered = True

    async def stop_accepting(self):
        if self._register_again_queue and self._register_again_consumer_tag:
            await self._register_again_queue.cancel(self._register_again_consumer_tag)
            self._register_again_consumer_tag = None

    async def stop(self):
        if self.connection:
            await self.connection.close()
            self.connection = None
            self.registry_admin_exchange = None

    async def _on_amqp_reconnect(self, connection):
        if self.container.shutting_down:
            return
        log.info("AMQP reconnected; registering with the registry.")
        await self.register()

    def _get_config(self):
        public = self.container.config.get("public")
        if isinstance(public, dict) and public:
            return public
        return {}

    @publish(REGISTER_RKEY)
    async def register(self):
        heartbeat_interval = get_heartbeat_interval(self.container.config)
        public_config = self._get_config()
        body = {
            "service_name": self.container.service_name,
            "instance_id": self.container.instance_id,
            "pid": self.container.pid,
            "host": self.container.host,
            "service_version": self.container.version,
            "kontiki_version": __version__,
            "heartbeat_interval": heartbeat_interval,
            "group": get_registration_group(self.container.config),
        }

        if public_config:
            body["config"] = public_config
        return body

    @publish(UNREGISTER_RKEY)
    async def unregister(self):
        body = {
            "service_name": self.container.service_name,
            "instance_id": self.container.instance_id,
        }
        return body

    @publish(HEARTBEAT_RKEY)
    async def heartbeat(self, degraded, reason=None):
        body = {
            "service_name": self.container.service_name,
            "instance_id": self.container.instance_id,
            "degraded": degraded,
        }
        if reason is not None:
            body["reason"] = reason
        return body

    @publish(EXCEPTION_RKEY)
    async def register_exception(self, exception, context):
        body = {
            "service_name": self.container.service_name,
            "instance_id": self.container.instance_id,
            "exception_type": type(exception).__name__,
            "message": str(exception),
            "context": context,
            "timestamp": datetime.now().isoformat(),
        }
        return body

    async def _register_again(self, message):
        if self.container.shutting_down:
            await message.nack(requeue=True)
            return
        async with message.process():
            try:
                service_name = self.container.service_name
                instance_id = self.container.instance_id
                service_str = f"{service_name}#{instance_id}"
                log.info("Re-registering service %s.", service_str)
                await self.register()
            except Exception as e:
                log.error("Error handling register_again message: %s", e)
