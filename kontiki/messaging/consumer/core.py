import uuid

from aio_pika import connect_robust

from kontiki.configuration.parameter import (
    get_kontiki_parameter,
    resolve_parameter_path,
)
from kontiki.messaging.common import (
    KONTIKI_SESSION_OPEN_RPC,
    create_tls_context,
    declare_event_exchange,
    declare_rpc_exchange,
    get_amqp_url,
)
from kontiki.messaging.consumer.event import OnEventTask
from kontiki.messaging.consumer.rpc import RpcTask
from kontiki.messaging.serialization import Serializer
from kontiki.utils import log


class Consumer:
    def __init__(self, container):
        self.container = container
        self.amqp_url = get_amqp_url(self.container.config)
        self.on_event_tasks = []
        self.rpc_tasks = []
        self.service_name = self.container.service_name
        self.connection = None

    async def setup(self):
        # Connect to RabbitMQ
        # Create SSL context if configured.
        tls_ctx = create_tls_context(self.container.config)
        self.connection = await connect_robust(self.amqp_url, ssl_context=tls_ctx)
        self.channel = await self.connection.channel()
        # Set QoS for AMQP channel
        prefetch_count = get_kontiki_parameter(
            self.container.config, "amqp.max_pending_messages", 10
        )
        await self.channel.set_qos(prefetch_count=prefetch_count)
        self.event_exchange = await declare_event_exchange(self.channel)
        self.rpc_exchange = await declare_rpc_exchange(self.channel)

        # Sets serializer
        self.serializer = Serializer(self.container.config)

        # Register internal Kontiki RPCs
        await self._add_internal_session_rpc()

    async def start(self):
        for task in self.on_event_tasks:
            await task.run()
        for task in self.rpc_tasks:
            await task.run()

    async def stop(self):
        if self.connection:
            await self.connection.close()

    async def _add_internal_session_rpc(self):
        """Register the internal Kontiki RPC used to open sessions."""

        async def _session_open_handler(container, _headers=None, **kwargs):
            session_id = str(uuid.uuid4())
            instance_id = str(container.instance_id)
            log.debug(
                "Session opened for service instance %s with ID: %s",
                instance_id,
                session_id,
            )
            return (instance_id, session_id)

        _session_open_handler._rpc_endpoint = {
            "name": KONTIKI_SESSION_OPEN_RPC,
            "include_headers": True,
        }

        await self.add_rpc_tasks([_session_open_handler])

    async def add_on_event_tasks(self, tasks):
        for task in tasks:
            task_data = task._on_event_endpoint
            event_type_or_key = task_data["event_type_or_key"]
            use_config = task_data["use_config"]
            target_instance = task_data["target_instance"]
            include_headers = task_data["include_headers"]
            requeue_on_error = task_data["requeue_on_error"]
            reject_on_redelivered = task_data["reject_on_redelivered"]
            broadcast = task_data.get("broadcast", False)

            # if use_config, search for the event_type in the conf from the path
            event_type = resolve_parameter_path(
                self.container.config, event_type_or_key, use_config
            )

            # Explicitly bind the task to the service instance
            # pylint: disable=unnecessary-dunder-call
            task = task.__get__(self.container.service_instance)

            # Declare queue
            if broadcast:
                # One queue per instance so that all instances receive the event.
                qname = (
                    f"{self.service_name}.{event_type}."
                    f"{self.container.instance_id}.queue"
                )
            else:
                # Single queue per service (competing consumers within the service).
                qname = f"{self.service_name}.{event_type}.queue"
            queue = await self.channel.declare_queue(qname, durable=True)

            # Define routing key regarding the target_instance param.
            # For per-instance (session) handlers we suffix with the
            # service instance_id.
            routing_key = (
                f"{event_type}.{self.container.instance_id}"
                if target_instance
                else event_type
            )
            # Bind queue to exchange with event type as the routing key
            await queue.bind(self.event_exchange, routing_key=routing_key)
            log.debug("Queue %s bound with routing key %s", qname, routing_key)

            # Declare and register the task
            on_event_task = OnEventTask(
                event_type,
                task,
                queue,
                self.serializer,
                include_headers,
                requeue_on_error,
                reject_on_redelivered,
            )
            self.on_event_tasks.append(on_event_task)
            log.debug("On event task registered for event: %s", event_type)

    async def add_rpc_tasks(self, tasks):
        for task in tasks:
            endpoint = task._rpc_endpoint
            task_name = endpoint["name"]
            include_headers = endpoint["include_headers"]

            # Declare queue
            routing_key = f"{self.service_name}.{task_name}"
            qname = f"{routing_key}.queue"
            queue = await self.channel.declare_queue(qname, durable=True)

            # Bind queue to exchange with event type as the routing key
            await queue.bind(self.rpc_exchange, routing_key=routing_key)
            log.debug("Queue %s bound with routing key %s", qname, routing_key)

            # Declare and register the task
            reply_exchange = self.channel.default_exchange
            rpc_task = RpcTask(
                task_name,
                task,
                self.container,
                reply_exchange,
                queue,
                self.serializer,
                include_headers,
            )
            self.rpc_tasks.append(rpc_task)
            log.debug("RPC task registered for task: %s", task_name)
