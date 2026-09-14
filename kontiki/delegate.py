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
        # Vestigial: the registry records the exception automatically if it
        # propagates (RPC, unmapped HTTP, @on_event, @task). Remove on next major.
        await self.container.report_exception(exception, context)
