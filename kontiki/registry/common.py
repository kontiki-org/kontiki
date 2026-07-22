from collections import defaultdict

from aio_pika import ExchangeType

from kontiki.configuration.parameter import get_kontiki_parameter

REGISTRY_ADMIN_EXCHANGE = "registry_admin_exchange"
REGISTRY_EVENT_EXCHANGE = "registry_event_exchange"
REGISTER_RKEY = "registry.register"
UNREGISTER_RKEY = "registry.unregister"
HEARTBEAT_RKEY = "registry.heartbeat"
EXCEPTION_RKEY = "registry.exception"
HEARTBEAT_DEFAULT_INTERVAL = 60
REGISTRATION_GROUP_DEFAULT = "business"


def get_event_queue_name(service_name, event):
    return f"{service_name}.{event}.queue"


async def declare_registry_admin_exchange(channel):
    return await channel.declare_exchange(REGISTRY_ADMIN_EXCHANGE, ExchangeType.TOPIC)


async def declare_registry_event_exchange(channel):
    return await channel.declare_exchange(REGISTRY_EVENT_EXCHANGE, ExchangeType.TOPIC)


def get_heartbeat_interval(config):
    return get_kontiki_parameter(
        config, "heartbeat.interval", HEARTBEAT_DEFAULT_INTERVAL
    )


def normalize_registration_group(value):
    if not isinstance(value, str):
        return REGISTRATION_GROUP_DEFAULT
    stripped = value.strip()
    if not stripped:
        return REGISTRATION_GROUP_DEFAULT
    return stripped


def get_registration_group(config):
    return normalize_registration_group(
        get_kontiki_parameter(config, "registration.group", default="")
    )


def nested_dict():
    return defaultdict(nested_dict)
