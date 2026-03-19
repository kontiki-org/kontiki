import logging

from kontiki.delegate import ServiceDelegate
from kontiki.messaging import on_event


class SimpleEventService:
    name = "SimpleEventService"

    @on_event("simple_event")
    async def handle_simple_event(self, payload):
        logging.info("Service received simple_event: %s", payload)

    @on_event("event.name", use_config=True)
    async def handle_dynamic_event_name(self, payload):
        logging.info("Service received event.name: %s", payload)

    @on_event(
        "retry_then_reject_event", requeue_on_error=True, reject_on_redelivered=True
    )
    async def handle_retry_then_reject(self, payload):
        logging.info("Service received retry_then_reject_event: %s", payload)
        logging.info(
            "First delivery will be requeued on error; "
            "a redelivered message will be rejected instead of requeued."
        )
        raise RuntimeError(
            "Simulated error for requeue_on_error/reject_on_redelivered example"
        )
