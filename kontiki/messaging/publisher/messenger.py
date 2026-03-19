import asyncio
import socket
import uuid
from datetime import datetime

from aio_pika import Message, connect_robust
from aio_pika.exceptions import ChannelInvalidStateError

from kontiki.delegate import ServiceDelegate
from kontiki.messaging.common import (
    AMQP_DEFAULT_URL,
    EVENT_EXCHANGE,
    KONTIKI_SESSION_OPEN_RPC,
    create_tls_context,
    declare_event_exchange,
    declare_rpc_exchange,
    get_amqp_url,
    get_rpc_timeout,
)
from kontiki.messaging.publisher.rpc import (
    RpcClientError,
    RpcServerError,
    RpcTimeoutError,
)
from kontiki.messaging.publisher.session import EventSession
from kontiki.messaging.rpc import RpcErrorType, RpcReturn
from kontiki.messaging.serialization import DEFAULT_SERIALIZATION, Serializer
from kontiki.utils import KONTIKI, get_kontiki_header_name, log, setup_logger


class Messenger(ServiceDelegate):
    def __init__(
        self,
        amqp_url=AMQP_DEFAULT_URL,
        event_exchange=EVENT_EXCHANGE,
        serialization=DEFAULT_SERIALIZATION,
        standalone=False,
        client_name="client",
    ):
        super().__init__()
        self.connection = None
        self.channel = None
        self.futures = {}
        self.callback_queue = None
        self.event_exchange_name = event_exchange
        self.serializer = None
        self.serialization = serialization
        self.amqp_url = amqp_url
        self.standalone = standalone
        self._reconnecting = False
        self._started = False

        # Identification differs between standalone and container-attached modes.
        if self.standalone:
            base_name = client_name
            if not base_name.startswith(f"{KONTIKI}-standalone-"):
                base_name = f"{KONTIKI}-standalone-{base_name}"
            self.service_name = base_name
            # Give each standalone client a stable instance id if not provided
            self.instance_id = str(uuid.uuid4())

    async def _setup(self, config):
        amqp_url = get_amqp_url(config, self.amqp_url)

        # Create SSL context if configured.
        tls_ctx = create_tls_context(config)

        self.connection = await connect_robust(amqp_url, ssl_context=tls_ctx)
        self.channel = await self.connection.channel()
        # Create exchanges for async and sync communications
        self.event_exchange = await declare_event_exchange(
            self.channel, self.event_exchange_name
        )
        self.rpc_exchange = await declare_rpc_exchange(self.channel)
        # Declare shared callback queue
        self.callback_queue = await self.channel.declare_queue(
            exclusive=True, auto_delete=True
        )
        # Sets serializer
        self.serializer = Serializer(config, serialization=self.serialization)
        # Cache RPC timeout from config (works both in container and standalone)
        self._rpc_timeout = get_rpc_timeout(config)

    async def setup(self):
        if self._started:
            return
        if self.standalone:
            if not log.hasHandlers():
                setup_logger()
            await self._setup({KONTIKI: {"amqp": {"url": self.amqp_url}}})
        else:
            await self._setup(self.container.config)
        self._started = True

    async def start(self):
        # Alias for standalone clients: start/stop feels more natural than setup/stop.
        await self.setup()

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.stop()
        return False

    async def stop(self):
        if self.connection:
            await self.connection.close()
            log.debug("AMQP Event Dispatcher connection closed.")
        self.connection = None
        self.channel = None
        self.callback_queue = None
        self._started = False

    async def publish(self, event_type, obj, reply_to=None, extra_headers=None):
        if extra_headers is None:
            extra_headers = {}

        event_headers = {
            "event_type": event_type,
            # reply_to is kept for advanced/legacy AMQP usage.
            # Normal Kontiki flows should prefer call() for request/reply.
            "reply_to": reply_to,
        }
        headers = self.get_service_headers() | event_headers | extra_headers
        message = self.serializer.dumps(obj)

        try:
            await self.event_exchange.publish(
                Message(body=message, headers=headers), routing_key=event_type
            )
        except ChannelInvalidStateError:
            log.info("Channel is in an invalid state. Attempting to reconnect...")
            await self.reconnect()
            await self.event_exchange.publish(
                Message(body=message, headers=headers), routing_key=event_type
            )

        log.debug("Event published: %s -> %s", event_type, message)

    async def call(
        self, service_name, method_name, *args, extra_headers=None, **kwargs
    ):
        cid = str(uuid.uuid4())
        loop = asyncio.get_running_loop()

        # Create a future to wait for the response
        future = loop.create_future()
        self.futures[cid] = future

        async def on_response(message):
            cid = message.correlation_id
            if cid in self.futures:
                future = self.futures.pop(cid)
                if not future.done():
                    try:
                        response = self.serializer.loads(message.body)
                        future.set_result(response)
                        log.debug(
                            "Response received for correlation_id=%s: %s", cid, response
                        )
                    except Exception as e:
                        future.set_exception(e)
                        log.error("Error processing response: %s", e)
                else:
                    log.warning("Response for %s already handled.", cid)
            else:
                log.warning("Unknown correlation_id: %s", cid)

        # Start consuming messages from the temporary queue
        await self.callback_queue.consume(on_response)

        # Sends the sync request
        if extra_headers is None:
            extra_headers = {}
        remote_headers = {"remote_method": method_name}
        headers = self.get_service_headers() | remote_headers | extra_headers

        routing_key = f"{service_name}.{method_name}"
        request_body = self.serializer.dumps({"args": args, "kwargs": kwargs})
        request_message = Message(
            body=request_body,
            correlation_id=cid,
            reply_to=self.callback_queue.name,
            headers=headers,
        )

        log.debug("Call: %s(args=%s, kwargs=%s)", method_name, args, kwargs)
        await self.rpc_exchange.publish(request_message, routing_key=routing_key)

        try:
            # Wait for the response with a timeout
            response = await asyncio.wait_for(future, timeout=self._rpc_timeout)
        except asyncio.TimeoutError:
            # Cleanup future on timeout
            if cid in self.futures:
                del self.futures[cid]
            raise RpcTimeoutError(method_name)

        if isinstance(response, RpcReturn):
            if response.success:
                return response.result

            if response.error_type == RpcErrorType.CLIENT:
                raise RpcClientError(method_name, response.error_code, response.message)
            else:
                raise RpcServerError(method_name, response.error_code, response.message)

        return response

    async def open_session(self, service_name):
        # Open an event session with a given service.
        # Calls the internal Kontiki RPC to open a session.
        instance_id, session_id = await self.call(
            service_name, KONTIKI_SESSION_OPEN_RPC
        )
        return EventSession(self, service_name, instance_id, session_id)

    async def reconnect(self):
        if self._reconnecting:
            return
        self._reconnecting = True
        try:
            log.info("Reconnecting to AMQP server...")
            if self.connection:
                await self.connection.close()
            await self.setup()
            log.info("Reconnected successfully.")
        finally:
            self._reconnecting = False

    def get_service_headers(self):
        if self.container:
            return {
                get_kontiki_header_name("service_name"): self.container.service_name,
                get_kontiki_header_name("instance_id"): str(self.container.instance_id),
                get_kontiki_header_name("host"): self.container.host,
                get_kontiki_header_name("timestamp"): datetime.now(),
            }
        return {
            get_kontiki_header_name("service_name"): self.service_name,
            get_kontiki_header_name("instance_id"): self.instance_id,
            get_kontiki_header_name("host"): socket.gethostname(),
            get_kontiki_header_name("timestamp"): datetime.now(),
        }
