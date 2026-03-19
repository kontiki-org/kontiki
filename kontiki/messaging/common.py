import ssl

from aio_pika import ExchangeType

from kontiki.configuration.parameter import get_kontiki_parameter
from kontiki.utils import KONTIKI

# -----------------------------------------------------------------------------

AMQP_DEFAULT_URL = "amqp://guest:guest@localhost/"
EVENT_EXCHANGE = "event_exchange"
RPC_EXCHANGE = "rpc_exchange"
KONTIKI_SESSION_OPEN_RPC = f"___{KONTIKI}__internal_session_open__"


async def declare_event_exchange(channel, name=EVENT_EXCHANGE):
    return await channel.declare_exchange(name, ExchangeType.TOPIC)


async def declare_rpc_exchange(channel, name=RPC_EXCHANGE):
    return await channel.declare_exchange(name, ExchangeType.TOPIC)


def get_amqp_url(config, default_url=AMQP_DEFAULT_URL):
    return get_kontiki_parameter(config, "amqp.url", default_url)


def get_rpc_timeout(config):
    return get_kontiki_parameter(config, "amqp.rpc.timeout", 10)


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
