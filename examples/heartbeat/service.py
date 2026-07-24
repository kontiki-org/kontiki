import logging

from kontiki.delegate import ServiceDelegate
from kontiki.messaging import rpc
from kontiki.registry import degraded_on


class HeartbeatExampleDelegate(ServiceDelegate):
    def __init__(self):
        self.degraded = False
        self.degraded_reason = None

    async def setup(self):
        logging.info("Heartbeat are automatically published by the service.")
        logging.info(
            "You can configure the heartbeat interval in the service configuration."
        )

    def set_degraded(self, degraded, reason=None):
        self.degraded = degraded
        self.degraded_reason = reason if degraded else None

    def is_degraded(self):
        if not self.degraded:
            return False
        if self.degraded_reason is not None:
            return True, self.degraded_reason
        return True


class HeartbeatExampleService:
    name = "heartbeat_example"
    delegate = HeartbeatExampleDelegate()

    @rpc
    async def set_degraded(self, degraded, reason=None):
        self.delegate.set_degraded(degraded, reason=reason)

    @degraded_on
    def is_degraded(self):
        logging.info(
            "This method is called at every heartbeat sent to the service registry to determine if the service is degraded."
        )
        logging.info("Return True, or (True, reason), to mark the service as degraded.")
        return self.delegate.is_degraded()
