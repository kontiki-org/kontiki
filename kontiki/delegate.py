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
        if not self.container:
            return
        await self.container.report_exception(exception, context)
