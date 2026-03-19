import logging

from kontiki.delegate import ServiceDelegate
from kontiki.messaging import on_event, rpc


class RegistryExampleDelegate(ServiceDelegate):
    async def setup(self):
        logging.info(
            "RegistryExampleDelegate setup – instance_id=%s", self.container.instance_id
        )

    async def start(self):
        logging.info("RegistryExampleDelegate start called.")

    async def stop(self):
        logging.info("RegistryExampleDelegate stop called.")

    async def raise_exception(self):
        try:
            raise Exception("This is a test exception")
        except Exception as e:
            await self.publish_exception(
                e, context={"message": "Whatever context you want to add."}
            )


class RegistryExampleService:
    """Example service that registers itself in the Kontiki registry."""

    name = "RegistryExampleService"
    delegate = RegistryExampleDelegate()

    @on_event("event_display_in_registry")
    async def handle_event_display_in_registry(self, payload):
        logging.info(
            "Event calls can be tracked in the registry. Check the registry service to see the event."
        )

    @rpc
    async def rpc_in_registry(self):
        logging.info(
            "RPC calls can also be tracked in the registry. Check the registry service to see the RPC."
        )

    @rpc
    async def raise_exception(self):
        logging.info("Publish an exception to the registry service.")
        await self.delegate.raise_exception()
