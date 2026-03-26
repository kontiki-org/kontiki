import asyncio
import logging
from datetime import datetime, timedelta, timezone

from kontiki.configuration.parameter import get_parameter
from kontiki.messaging.common import declare_event_exchange, declare_rpc_exchange
from kontiki.registry.common import declare_registry_event_exchange
from kontiki.utils import get_kontiki_prefix

# -----------------------------------------------------------------------------


class EventTracker:
    def __init__(self, core):
        self.core = core
        self.consumers = {}
        self.events = []

    async def setup(self):
        self.event_ttl_minutes = get_parameter(
            self.core.container.config, "event_tracker.ttl_minutes", 0
        )

        self.event_ttl_hours = get_parameter(
            self.core.container.config, "event_tracker.ttl_hours", 24 * 7
        )

        # Use minutes if set, otherwise use hours.
        if self.event_ttl_minutes > 0:
            self.event_ttl = self.event_ttl_minutes
        elif self.event_ttl_hours > 0:
            self.event_ttl = self.event_ttl_hours * 60

        self.disable_tracking = get_parameter(
            self.core.container.config, "event_tracker.disable", False
        )

        self.cleanup_interval = get_parameter(
            self.core.container.config, "event_tracker.cleanup_interval_seconds", 3600
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

            self.cleanup_task = asyncio.create_task(self._cleanup_events())
            logging.debug("EventTracker setup completed.")
        except Exception as e:
            logging.error("Error creating or consuming queue %s: %s", queue_name, e)

    async def _handle_event(self, message):
        async with message.process():
            try:
                raw_headers = message.headers or {}

                # Normalise Kontiki-specific headers while preserving all headers.
                normalized = dict(raw_headers)
                prefix = get_kontiki_prefix()
                for key, value in raw_headers.items():
                    if key.startswith(prefix):
                        bare_key = key[len(prefix) :]
                        # Do not overwrite potential user headers with the same name.
                        normalized.setdefault(bare_key, value)

                event_type = normalized.get("event_type", "_rpc_event")
                service = normalized.get("service_name")
                uuid = normalized.get("instance_id")
                host = normalized.get("host")
                logging.debug(
                    "Received %s from %s#%s [%s]", event_type, service, uuid, host
                )
                self.events.append(normalized)

            except Exception as e:
                logging.error("Error processing event: %s", e)

    async def _cleanup_events(self):
        logging.info(
            "Starting cleanup task with %s seconds." "interval (TTL: %s minutes)",
            self.cleanup_interval,
            self.event_ttl,
        )

        while True:
            try:
                self._purge_expired_events()

                await asyncio.sleep(self.cleanup_interval)
            except asyncio.CancelledError:
                logging.info("Cleanup task cancelled.")
                break
            except Exception as e:
                logging.error("Error during cleanup task: %s", e)

    def is_disabled(self):
        if self.disable_tracking:
            logging.info("Event tracking is disabled.")
        return self.disable_tracking

    def _purge_expired_events(self):
        expiration_time = datetime.now(timezone.utc) - timedelta(minutes=self.event_ttl)
        cutoff = 0
        for index, event in enumerate(self.events):
            event_timestamp = event.get("timestamp")
            if event_timestamp is None:
                cutoff = index + 1
                continue

            if isinstance(event_timestamp, str):
                try:
                    event_timestamp = datetime.fromisoformat(event_timestamp)
                except Exception:
                    logging.warning("Invalid timestamp format: %s", event_timestamp)
                    cutoff = index + 1
                    continue

            # Normalise to UTC-aware datetime to avoid naive/aware comparisons.
            if isinstance(event_timestamp, datetime):
                if event_timestamp.tzinfo is None:
                    event_timestamp = event_timestamp.replace(tzinfo=timezone.utc)
                else:
                    event_timestamp = event_timestamp.astimezone(timezone.utc)

            if event_timestamp <= expiration_time:
                cutoff = index + 1
                continue

            # Keep events that are not expired.
            break

        # Remove expired events.
        if cutoff > 0:
            del self.events[:cutoff]
            logging.debug("Cleaned up %s expired events.", cutoff)
        else:
            logging.debug("No expired events found.")
