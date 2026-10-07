import ssl

from aio_pika import ExchangeType

from kontiki.configuration.parameter import get_kontiki_parameter
from kontiki.utils import KONTIKI

# -----------------------------------------------------------------------------

AMQP_DEFAULT_URL = "amqp://guest:guest@localhost/"
EVENT_EXCHANGE = "event_exchange"
RPC_EXCHANGE = "rpc_exchange"
FAILED_EXCHANGE = "kontiki.failed"
FAILED_QUEUE_MAX_LENGTH = 10000
DELAYED_RETRY_MIN_MS = 1000
DELAYED_RETRY_MAX_MS = 30000
KONTIKI_SESSION_OPEN_RPC = f"___{KONTIKI}__internal_session_open__"

# AMQP delivery modes
DELIVERY_MODE_PERSISTENT = 2


async def declare_event_exchange(channel, name=EVENT_EXCHANGE):
    return await channel.declare_exchange(name, ExchangeType.TOPIC)


async def declare_rpc_exchange(channel, name=RPC_EXCHANGE):
    return await channel.declare_exchange(name, ExchangeType.TOPIC)


async def declare_failed_exchange(channel, name=FAILED_EXCHANGE):
    return await channel.declare_exchange(name, ExchangeType.DIRECT, durable=True)


def failed_queue_name(service_name, event_type):
    return f"{service_name}.{event_type}.failed"


def get_amqp_url(config, default_url=AMQP_DEFAULT_URL):
    return get_kontiki_parameter(config, "amqp.url", default_url)


def is_amqp_required(config):
    return get_kontiki_parameter(config, "amqp.required", True)


def is_amqp_disabled(config):
    return get_kontiki_parameter(config, "amqp.disable", False)


def check_amqp_disable(config):
    if not is_amqp_disabled(config):
        return
    # None means the key is absent. The real defaults would look like a conflict.
    if get_kontiki_parameter(config, "amqp.required", None) is True:
        raise ValueError(
            "kontiki.amqp.disable and kontiki.amqp.required cannot both be true."
        )
    if get_kontiki_parameter(config, "registration.disable", None) is False:
        raise ValueError(
            "kontiki.amqp.disable cannot be combined with "
            "kontiki.registration.disable: false."
        )


def get_rpc_timeout(config):
    return get_kontiki_parameter(config, "amqp.rpc.timeout", 10)


def get_grace_seconds(config):
    return get_kontiki_parameter(config, "shutdown.grace_seconds", 25)


def create_tls_context(config):
    config = get_kontiki_parameter(config, "amqp.tls", {})

    if not isinstance(config, dict):
        return None

    if not config.get("enabled", False):
        return None

    context = ssl.create_default_context(cafile=config["ca_cert"])
    client_cert = config.get("client_cert", None)
    client_key = config.get("client_key", None)
    if client_cert and client_key:
        context.load_cert_chain(certfile=client_cert, keyfile=client_key)
    return context
