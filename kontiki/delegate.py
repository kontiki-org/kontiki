from kontiki.utils import log


class ServiceDelegate:
    def __init__(self):
        self.container = None

    def bind(self, container, attr_name):
        self.container = container
        self.attr_name = attr_name

    async def setup(self):
        pass

    async def start(self):
        pass

    async def stop(self):
        pass

    async def publish_exception(self, exception, context=None):
        if context is None:
            context = {}

        if not self.container or not self.container.service_registry_client:
            log.warning("Service registration is disabled or unavailable..")
            return

        try:
            await self.container.service_registry_client.register_exception(
                exception, context
            )
            log.debug("Exception published successfully: %s.", exception)
        except Exception as e:
            log.error("Error while publishing exception %s: %s", exception, e)
