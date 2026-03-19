import asyncio

from aio_pika import IncomingMessage

from kontiki.utils import log


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
        event_type_or_key: Static event name or configuration key.
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
    ):
        self.event_type = event_type
        self.task = task
        self.queue = queue
        self.serializer = serializer
        self.include_headers = include_headers
        self.requeue_on_error = requeue_on_error
        self.reject_on_redelivered = reject_on_redelivered

    async def run(self):
        async def consume_message(message: IncomingMessage):
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

        await self.queue.consume(consume_message)
