import logging

from kontiki.delegate import ServiceDelegate
from kontiki.messaging import rpc
from kontiki.registry import degraded_on


class HeartbeatExampleDelegate(ServiceDelegate):
    def __init__(self):
        self.degraded = False

    async def setup(self):
        logging.info("Heartbeat are automatically published by the service.")
        logging.info(
            "You can configure the heartbeat interval in the service configuration."
        )

    def set_degraded(self, degraded: bool):
        self.degraded = degraded

    def is_degraded(self):
        return self.degraded


class HeartbeatExampleService:
    name = "heartbeat_example"
    delegate = HeartbeatExampleDelegate()

    @rpc
    async def set_degraded(self, degraded: bool):
        self.delegate.set_degraded(degraded)

    @degraded_on
    def is_degraded(self):
        logging.info(
            "This method is called at every heartbeat sent to the service registry to determine if the service is degraded."
        )
        logging.info("If it returns True, the service will be marked as degraded.")
        return self.delegate.is_degraded()
