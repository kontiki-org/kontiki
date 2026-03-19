import asyncio
from datetime import datetime

from aio_pika import Message, connect_robust

from kontiki.configuration.parameter import get_kontiki_parameter
from kontiki.messaging.common import create_tls_context, get_amqp_url
from kontiki.messaging.serialization import Serializer
from kontiki.registry.common import (
    EXCEPTION_RKEY,
    HEARTBEAT_RKEY,
    REGISTER_RKEY,
    UNREGISTER_RKEY,
    declare_registry_admin_exchange,
    get_heartbeat_interval,
)
from kontiki.utils import log

# -----------------------------------------------------------------------------


def filter_config_by_whitelist(config, whitelist_patterns):
    if not whitelist_patterns:
        return {}

    def _is_included(path):
        for pattern in whitelist_patterns:
            if path == pattern or path.startswith(f"{pattern}."):
                return True
        return False

    def _filter_dict(d, parent_path=""):
        filtered = {}
        for key, value in d.items():
            current_path = f"{parent_path}.{key}" if parent_path else key

            if _is_included(current_path):
                if isinstance(value, dict):
                    filtered[key] = _filter_dict(value, current_path)
                else:
                    filtered[key] = value
            elif isinstance(value, dict):
                nested_filtered = _filter_dict(value, current_path)
                if nested_filtered:
                    filtered[key] = nested_filtered
        return filtered

    return _filter_dict(config)


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
            log.info("Published message to %s: %s", routing_key, body)

        return wrapper

    return decorator


# -----------------------------------------------------------------------------


class ServiceRegistryClient:
    def __init__(self, container):
        self.container = container
        self.connection = None
        self.channel = None
        self.registry_admin_exchange = None

    async def setup(self):
        log.debug("ServiceRegistryClient Setup")
        amqp_url = get_amqp_url(self.container.config)
        ssl_ctx = create_tls_context(self.container.config)
        self.connection = await connect_robust(amqp_url, ssl_context=ssl_ctx)
        self.channel = await self.connection.channel()
        await self.channel.set_qos(prefetch_count=10)
        self.registry_admin_exchange = await declare_registry_admin_exchange(
            self.channel
        )
        self.serializer = Serializer(self.container.config)

        queue_name = "register_again.queue"
        queue = await self.channel.declare_queue(queue_name, durable=True)
        service_name = self.container.service_name
        instance_id = self.container.instance_id
        routing_key = f"{service_name}.{instance_id}.register_again"
        await queue.bind(self.registry_admin_exchange, routing_key=routing_key)
        await queue.consume(self._register_again)

        # Delay registration to ensure the ServiceRegistry is fully ready to
        # receive messages. This helps avoid lost registration messages during startup.

        delay = get_kontiki_parameter(
            self.container.config, "registration.delay", default=2
        )
        log.info("Delaying registration by %s seconds.", delay)
        await asyncio.sleep(delay)
        await self.register()

    async def stop(self):
        if self.connection:
            await self.connection.close()

    def _get_config(self):
        config = self.container.config
        public_paths = get_kontiki_parameter(
            config, "registration.configuration.public_paths", default=None
        )
        if public_paths:
            return filter_config_by_whitelist(config, public_paths)
        return {}

    @publish(REGISTER_RKEY)
    async def register(self):
        heartbeat_interval = get_heartbeat_interval(self.container.config)
        filtered_config = self._get_config()
        body = {
            "service_name": self.container.service_name,
            "instance_id": self.container.instance_id,
            "pid": self.container.pid,
            "host": self.container.host,
            "service_version": self.container.version,
            "heartbeat_interval": heartbeat_interval,
        }

        if filtered_config:
            body["config"] = filtered_config
        return body

    @publish(UNREGISTER_RKEY)
    async def unregister(self):
        body = {
            "service_name": self.container.service_name,
            "instance_id": self.container.instance_id,
        }
        return body

    @publish(HEARTBEAT_RKEY)
    async def heartbeat(self, degraded):
        body = {
            "service_name": self.container.service_name,
            "instance_id": self.container.instance_id,
            "degraded": degraded,
        }
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
        async with message.process():
            try:
                service_name = self.container.service_name
                instance_id = self.container.instance_id
                service_str = f"{service_name}#{instance_id}"
                log.info("Re-registering service %s.", service_str)
                await self.register()
            except Exception as e:
                log.error("Error handling register_again message: %s", e)
