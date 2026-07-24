import asyncio

from kontiki.delegate import ServiceDelegate
from kontiki.registry.common import get_heartbeat_interval
from kontiki.utils import log

# -----------------------------------------------------------------------------


def degraded_on(func):
    func._degraded = True
    return func


def normalize_degraded_result(result):
    # Accept bool (legacy) or (degraded, reason).
    if isinstance(result, tuple) and len(result) == 2:
        degraded, reason = result
        if not degraded:
            return False, None
        if reason is None:
            return True, None
        return True, str(reason)
    if result:
        return True, None
    return False, None


# -----------------------------------------------------------------------------


class HeartbeatPublisher(ServiceDelegate):
    def __init__(self, service_registry_client):
        self.interval = None
        self.task = None
        self.service_registry_client = service_registry_client
        self.stop_condition = None
        self._is_degraded = False
        super().__init__()

    async def setup(self):
        if self.service_registry_client:
            self.interval = get_heartbeat_interval(self.container.config)
            log.debug("Heartbeat interval set to %s", self.interval)

            service_instance = self.container.service_instance
            for attr_name in dir(service_instance):
                attr = getattr(service_instance, attr_name)
                if callable(attr) and getattr(attr, "_degraded", False):
                    self.stop_condition = attr
                    break
        else:
            log.info("Service registration is disabled.")

    async def start(self):
        if self.service_registry_client:
            self.task = asyncio.create_task(self._send_heartbeat())

    async def stop(self):
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass

    async def _send_heartbeat(self):
        log.info("Starting heartbeat task.")
        error_logged = False
        while True:
            try:
                should_degrade, reason = self._evaluate_degraded()

                # Normal state -> degraded state
                if should_degrade and not self._is_degraded:
                    self._is_degraded = True
                    if reason:
                        log.info("Service entered degraded state: %s", reason)
                    else:
                        log.info("Service entered degraded state.")

                # Degraded state -> Normal state
                elif not should_degrade and self._is_degraded:
                    self._is_degraded = False
                    reason = None
                    log.info("Service recovered from degraded state.")

                if not self._is_degraded:
                    reason = None

                await self.service_registry_client.heartbeat(
                    self._is_degraded, reason=reason
                )

                if self.interval is not None:
                    await asyncio.sleep(self.interval)
                else:
                    # Default to 10 seconds if interval is not set
                    await asyncio.sleep(10)

            except asyncio.CancelledError:
                log.info("Heartbeat task was cancelled.")
                break
            except Exception as e:
                # To avoid log messages to be printed indefinitely.
                if not error_logged:
                    log.error("Error in heartbeat task: %s", e)
                    error_logged = True

    def _evaluate_degraded(self):
        if not self.stop_condition:
            return False, None
        return normalize_degraded_result(self.stop_condition())
