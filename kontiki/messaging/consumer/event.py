import asyncio

from aio_pika import IncomingMessage

from kontiki.messaging.flow import enter_flow_from_headers, reset_flow_id
from kontiki.utils import log


def normalize_event_types(value):
    """Normalize a string or list of strings to a non-empty list of event types."""
    if isinstance(value, str):
        event_types = [value]
    elif isinstance(value, list):
        event_types = value
    else:
        raise ValueError(
            "on_event(): event type must be a string or a list of strings, "
            f"got {type(value).__name__}"
        )
    if not event_types:
        raise ValueError("on_event(): event type list must not be empty")
    for event_type in event_types:
        if not isinstance(event_type, str) or not event_type:
            raise ValueError(
                "on_event(): each event type must be a non-empty string, "
                f"got {event_type!r}"
            )
    return event_types


def on_event(
    event_type_or_key,
    use_config: bool = False,
    *,
    include_headers: bool = False,
    requeue_on_error: bool = False,
    reject_on_redelivered: bool = False,
    in_session: bool = False,
    broadcast: bool = False,
):
    """Declare an event handler for a Kontiki service.

    Args:
        event_type_or_key: Static event name, list of event names, or configuration
            key when use_config is True. Resolved config values may be a string or
            a list of strings. An empty list fails fast at startup.
        use_config: When True, resolve event_type_or_key from configuration.
        include_headers: When True, pass AMQP headers to the handler via _headers.
        requeue_on_error: When True, requeue messages on handler error.
        reject_on_redelivered: When True, reject messages that were already redelivered.
        in_session: When True, the event is scoped to a specific service instance
            and session. This is a higher-level flag; internally it implies
            routing to a single instance.
        broadcast: When True, every instance of the service will receive the
            event (no competing consumers within the service).
    """

    def decorator(handler):
        if in_session and broadcast:
            raise ValueError(
                "on_event(): 'in_session' and 'broadcast' cannot both be True."
            )
        if not use_config:
            normalize_event_types(event_type_or_key)
        handler._on_event_endpoint = {
            "event_type_or_key": event_type_or_key,
            "use_config": use_config,
            # target_instance is an internal detail; it is derived from in_session.
            "target_instance": in_session,
            "include_headers": include_headers,
            "requeue_on_error": requeue_on_error,
            "reject_on_redelivered": reject_on_redelivered,
            "broadcast": broadcast,
        }
        return handler

    return decorator


class OnEventTask:
    def __init__(
        self,
        event_type,
        task,
        queue,
        serializer,
        include_headers,
        requeue_on_error,
        reject_on_redelivered,
        container,
    ):
        self.event_type = event_type
        self.task = task
        self.queue = queue
        self.serializer = serializer
        self.include_headers = include_headers
        self.requeue_on_error = requeue_on_error
        self.reject_on_redelivered = reject_on_redelivered
        self.container = container
        self._consumer_tag = None

    async def stop_accepting(self):
        if self._consumer_tag:
            await self.queue.cancel(self._consumer_tag)
            self._consumer_tag = None

    async def run(self):
        async def consume_message(message: IncomingMessage):
            if self.container.shutting_down:
                await message.nack(requeue=True)
                return

            handler_task = asyncio.create_task(self._consume_message(message))
            self.container.amqp_consumer.register_handler_task(handler_task)
            try:
                await handler_task
            finally:
                self.container.amqp_consumer.unregister_handler_task(handler_task)

        self._consumer_tag = await self.queue.consume(consume_message)

    async def _consume_message(self, message):
        work_in_flight = self.container.amqp_consumer.work_in_flight
        work_in_flight.begin()
        flow_token = enter_flow_from_headers(message.headers)
        try:
            try:
                log.debug(
                    "Consuming event %s (redelivered=%s, headers=%s)",
                    self.event_type,
                    message.redelivered,
                    message.headers,
                )
                async with message.process(
                    requeue=self.requeue_on_error,
                    reject_on_redelivered=self.reject_on_redelivered,
                ):
                    obj = self.serializer.loads(message.body)
                    log.info(
                        "Message received on %s: %s", self.event_type, message.body
                    )

                    headers = message.headers if self.include_headers else {}
                    if asyncio.iscoroutinefunction(self.task):
                        if headers:
                            await self.task(obj, _headers=headers)
                        else:
                            await self.task(obj)
                    else:
                        if headers:
                            self.task(obj, _headers=headers)
                        else:
                            self.task(obj)

            except Exception as e:
                log.error("Error occurred while consuming the event: %s", e)
                await message.nack(requeue=False)
        finally:
            work_in_flight.end()
            reset_flow_id(flow_token)
