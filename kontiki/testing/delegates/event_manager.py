import logging
import threading
import time

from kontiki.delegate import ServiceDelegate

# -----------------------------------------------------------------------------


class EventManager(ServiceDelegate):
    def __init__(self):
        self.events = []
        self._lock = threading.Lock()
        self._condition = threading.Condition(self._lock)
        super().__init__()

    def store_event(self, event):
        logging.info("Storing event %s.", event)
        with self._condition:
            self.events.append(event)
            self._condition.notify_all()

    def get_events(self, wait_for_events, timeout=None):
        with self._condition:
            if wait_for_events <= 0:
                return self.events.copy()
            start_time = time.time()
            while len(self.events) < wait_for_events:
                if timeout and (time.time() - start_time) > timeout:
                    logging.warning(
                        "Timeout waiting for %s events after %.2f seconds, got %s.",
                        wait_for_events,
                        timeout,
                        len(self.events),
                    )
                    break
                logging.info(
                    "Waiting for %s events, currently have %s.",
                    wait_for_events,
                    len(self.events),
                )
                remaining = timeout - (time.time() - start_time) if timeout else 1.0
                wait_time = min(1.0, max(0.0, remaining))
                self._condition.wait(timeout=wait_time)

            if not self.events:
                logging.warning("No events stored.")
                return []
            return self.events.copy()

    def clean(self):
        logging.info("Cleaning events.")
        with self._lock:
            self.events.clear()
