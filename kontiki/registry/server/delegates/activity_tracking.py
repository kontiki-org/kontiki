import asyncio
import logging
from datetime import datetime, timedelta, timezone

from kontiki.configuration.parameter import get_parameter
from kontiki.messaging.common import declare_event_exchange, declare_rpc_exchange
from kontiki.registry.common import (
    CONTEXT_RKEY,
    EXCEPTION_RKEY,
    declare_registry_event_exchange,
)
from kontiki.registry.events import CONTEXT_RECORDED, EXCEPTION_RECORDED

# Event types kept out of the timeline: each has its own dedicated store.
TIMELINE_EXCLUDED_EVENTS = frozenset({EXCEPTION_RECORDED})

# -----------------------------------------------------------------------------


class ActivityTracker:
    """Records registry activity: bus hops and contexts in the event timeline,
    exception records in their own store. Both share one retention policy."""

    def __init__(self, core):
        self.core = core
        self.events = []
        self.exceptions = []

    async def setup(self):
        self.ttl_minutes = get_parameter(
            self.core.container.config, "activity_tracker.ttl_minutes", 0
        )

        self.ttl_hours = get_parameter(
            self.core.container.config, "activity_tracker.ttl_hours", 24 * 7
        )

        # Use minutes if set, otherwise use hours.
        if self.ttl_minutes > 0:
            self.ttl = self.ttl_minutes
        elif self.ttl_hours > 0:
            self.ttl = self.ttl_hours * 60

        self.disable_tracking = get_parameter(
            self.core.container.config, "activity_tracker.disable", False
        )

        self.cleanup_interval = get_parameter(
            self.core.container.config,
            "activity_tracker.cleanup_interval_seconds",
            3600,
        )

        if self.is_disabled():
            return

        queue_name = "event_tracker.queue"
        try:
            self.registry_event_exchange = await declare_registry_event_exchange(
                self.core.channel
            )
            event_exchange = await declare_event_exchange(self.core.channel)
            rpc_exchange = await declare_rpc_exchange(self.core.channel)
            await self.registry_event_exchange.bind(event_exchange, routing_key="#")
            await self.registry_event_exchange.bind(rpc_exchange, routing_key="#")
            queue = await self.core.channel.declare_queue(queue_name, durable=True)
            await queue.bind(self.registry_event_exchange, routing_key="#")
            await queue.consume(self._handle_event)

            logging.debug("Timeline queue %s set up.", queue_name)
        except Exception as e:
            logging.error("Error creating or consuming queue %s: %s", queue_name, e)

        # Exceptions and contexts each keep their entry path, with the same
        # retention as the timeline.
        await self.core.create_and_consume_queue(
            EXCEPTION_RKEY, self._handle_exception
        )
        await self.core.create_and_consume_queue(CONTEXT_RKEY, self._handle_context)

        self.cleanup_task = asyncio.create_task(self._cleanup())
        logging.debug("ActivityTracker setup completed.")

    def is_disabled(self):
        if self.disable_tracking:
            logging.info("Activity tracking is disabled.")
        return self.disable_tracking

    async def _handle_event(self, message):
        async with message.process():
            try:
                headers = message.headers or {}
                event_type = headers.get("event_type", "_rpc_event")
                if event_type in TIMELINE_EXCLUDED_EVENTS:
                    return
                service = headers.get("service_name")
                uuid = headers.get("instance_id")
                host = headers.get("host")
                logging.debug(
                    "Received %s from %s#%s [%s]", event_type, service, uuid, host
                )
                self.events.append(dict(headers))

            except Exception as e:
                logging.error("Error processing event: %s", e)

    async def _handle_context(self, message):
        async with message.process():
            try:
                data = self.core.serializer.loads(message.body)
                self.events.append({**data, "event_type": CONTEXT_RECORDED})
            except Exception as e:
                logging.error("Error processing context: %s", e)

    async def _handle_exception(self, message):
        async with message.process():
            logging.debug("Received exception: %s", message.body)
            try:
                data = self.core.serializer.loads(message.body)
                self.exceptions.append(data)
                logging.debug("Exception recorded: %s", data)
                await self.core.on_exception_recorded(data)
            except Exception as e:
                logging.error("Error processing exception: %s", e)

    def get_exceptions(self):
        return self.exceptions

    async def _cleanup(self):
        logging.info(
            "Starting cleanup task with %s seconds." "interval (TTL: %s minutes)",
            self.cleanup_interval,
            self.ttl,
        )

        while True:
            try:
                self._purge_expired(self.events)
                self._purge_expired(self.exceptions)
                await asyncio.sleep(self.cleanup_interval)
            except asyncio.CancelledError:
                logging.info("Cleanup task cancelled.")
                break
            except Exception as e:
                logging.error("Error during cleanup task: %s", e)
                # Avoid a tight error loop that can spam logs and fill disk.
                await asyncio.sleep(self.cleanup_interval)

    def _purge_expired(self, items):
        expiration_time = datetime.now(timezone.utc) - timedelta(minutes=self.ttl)
        cutoff = 0
        for index, item in enumerate(items):
            item_timestamp = item.get("timestamp")
            if item_timestamp is None:
                cutoff = index + 1
                continue

            if isinstance(item_timestamp, str):
                try:
                    item_timestamp = datetime.fromisoformat(item_timestamp)
                except Exception:
                    logging.warning("Invalid timestamp format: %s", item_timestamp)
                    cutoff = index + 1
                    continue

            # Normalise to UTC-aware datetime to avoid naive/aware comparisons.
            if isinstance(item_timestamp, datetime):
                if item_timestamp.tzinfo is None:
                    item_timestamp = item_timestamp.replace(tzinfo=timezone.utc)
                else:
                    item_timestamp = item_timestamp.astimezone(timezone.utc)

            if item_timestamp <= expiration_time:
                cutoff = index + 1
                continue

            # Keep items that are not expired.
            break

        # Remove expired entries.
        if cutoff > 0:
            del items[:cutoff]
            logging.debug("Cleaned up %s expired entries.", cutoff)
        else:
            logging.debug("No expired entries found.")
