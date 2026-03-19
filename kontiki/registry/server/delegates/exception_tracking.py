import asyncio
import logging
from datetime import datetime, timedelta

from kontiki.configuration.parameter import get_parameter
from kontiki.registry.common import EXCEPTION_RKEY


class ExceptionTracker:
    def __init__(self, core):
        self.core = core
        self.exceptions = []

    async def setup(self):
        self.exception_ttl_minutes = get_parameter(
            self.core.container.config, "exception_tracker.ttl_minutes", 0
        )

        self.exception_ttl_hours = get_parameter(
            self.core.container.config, "exception_tracker.ttl_hours", 24 * 7
        )

        # Use minutes if set, otherwise use hours.
        if self.exception_ttl_minutes > 0:
            self.exception_ttl = self.exception_ttl_minutes
        elif self.exception_ttl_hours > 0:
            self.exception_ttl = self.exception_ttl_hours * 60

        self.disable_tracking = get_parameter(
            self.core.container.config, "exception_tracker.disable", False
        )

        self.cleanup_interval = get_parameter(
            self.core.container.config,
            "exception_tracker.cleanup_interval_seconds",
            3600,
        )

        if self.is_disabled():
            return

        await self.core.create_and_consume_queue(EXCEPTION_RKEY, self._handle_exception)
        self.cleanup_task = asyncio.create_task(self._cleanup_exceptions())
        logging.debug("ExceptionTracker setup completed.")

    async def _handle_exception(self, message):
        async with message.process():
            logging.debug("Received exception: %s", message.body)
            try:
                data = self.core.serializer.loads(message.body)
                await self.store_exception(data)

            except Exception as e:
                logging.error("Error processing exception: %s", e)

    async def store_exception(self, exception_data):
        logging.debug("Storing exception %s", exception_data)
        if self.is_disabled():
            return

        try:
            self.exceptions.append(exception_data)
            logging.debug("Exception recorded: %s", exception_data)
        except Exception as e:
            logging.error("Error recording exception: %s", e)

    async def _cleanup_exceptions(self):
        logging.info(
            "Starting cleanup task with %s seconds." "interval (TTL: %s minutes)",
            self.cleanup_interval,
            self.exception_ttl,
        )

        while True:
            try:
                self._purge_expired_exceptions()
                await asyncio.sleep(self.cleanup_interval)

            except asyncio.CancelledError:
                logging.info("Cleanup task cancelled.")
                break

            except Exception as e:
                logging.error("Error during cleanup task: %s", e)

    def is_disabled(self):
        if self.disable_tracking:
            logging.info("Exception tracking is disabled.")
        return self.disable_tracking

    def get_exceptions(self):
        return self.exceptions

    def _purge_expired_exceptions(self):
        expiration_time = datetime.now() - timedelta(minutes=self.exception_ttl)

        index = len(self.exceptions)
        cutoff = 0
        for index, exception in enumerate(self.exceptions):
            exception_timestamp = exception.get("timestamp")
            if exception_timestamp is None:
                cutoff = index + 1
                continue

            if isinstance(exception_timestamp, str):
                try:
                    exception_timestamp = datetime.fromisoformat(exception_timestamp)
                except Exception:
                    logging.warning("Invalid timestamp format: %s", exception_timestamp)
                    cutoff = index + 1
                    continue

            if exception_timestamp <= expiration_time:
                cutoff = index + 1
                continue

            # Keep exceptions that are not expired. Break the loop.
            break

        # Remove expired exceptions.
        if cutoff > 0:
            del self.exceptions[:cutoff]
            logging.debug("Cleaned up %s expired exceptions.", cutoff)
        else:
            logging.debug("No expired exceptions found.")
