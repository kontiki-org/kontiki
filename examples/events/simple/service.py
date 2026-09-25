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

    # Removed in V2.0: requeue_on_error and reject_on_redelivered are now handled
    # by RabbitMQ via max_attempts. Retry logic is managed by the broker, not Kontiki.
