import asyncio
import logging

from kontiki.container import ServiceContainer
from kontiki.messaging.publisher.messenger import Messenger

# -----------------------------------------------------------------------------

DEFAULT_CONF = {"kontiki": {"amqp": {"url": "amqp://guest:guest@localhost/"}}}

# -----------------------------------------------------------------------------


class MockServiceManager:
    def __init__(self, log_file, log_level="INFO", messenger=None, default_config=None):
        self.mock_args = {}
        self.mocks = {}
        self.event_conditions = {}
        self.messenger = messenger if messenger else Messenger(standalone=True)
        self._setup = False
        self.default_dummy_added = False
        self.default_service_config = default_config or DEFAULT_CONF

        format_ = (
            "%(asctime)s - %(levelname)s - %(message)s - %(filename)s - %(lineno)d"
        )

        self.logging_conf = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {"default": {"format": format_}},
            "handlers": {
                "file": {
                    "class": "logging.FileHandler",
                    "formatter": "default",
                    "level": log_level,
                    "filename": log_file,
                }
            },
            "root": {"level": "DEBUG", "handlers": ["file"]},
        }

    # Service management.
    def add(self, mock_class, config):
        name = mock_class.name if hasattr(mock_class, "name") else mock_class.__name__
        self.mock_args[name] = (mock_class, config)

    async def start(self):
        if not self.mock_args:
            # We add a DummyService so that the tester can use the MockServiceRunner
            # just to publish events or call a remote function without writing a
            # MockService they don't really need.
            class DefaultDummyService:
                name = "dummy_service"

                async def do_nothing(self):
                    pass

            logging.info("No services registered. Adding DefaultDummyService.")
            dummy_config = {"logging": self.logging_conf} | self.default_service_config
            self.add(DefaultDummyService, config=dummy_config)
            self.default_dummy_added = True

        for mock_name, args in self.mock_args.items():
            logging.info("Starting %s mock service with args = %s", mock_name, args)

            self.mocks[mock_name] = await self.start_service(*args)
            self.event_conditions[mock_name] = asyncio.Condition()

    async def stop(self):
        for _, (container, _) in self.mocks.items():
            await container.stop()
        self.mocks.clear()
        self.event_conditions.clear()
        if self.default_dummy_added:
            logging.info("DefaultDummyService stopped.")

        if hasattr(self.messenger, "stop") and self.messenger:
            await self.messenger.stop()

    async def start_service(self, service_cls, config):
        config["logging"] = self.logging_conf

        container = ServiceContainer(
            service_cls=service_cls,
            version="0.0.0",
            config_paths=[],
            disable_service_registration=True,
            config=config,
        )

        await container.setup()
        await container.start()
        return container, container.service_instance

    # Inputs and Outputs management.
    def get_events(self, mock_name, wait_for_events=0, timeout=None):
        return self.get_service(mock_name).get_events(wait_for_events, timeout)

    def clean_events(self, mock_name):
        self.get_service(mock_name).clean_events()

    def add_http_response(self, mock_name, response):
        self.get_service(mock_name).add_http_response(response)

    def get_http_requests(self, mock_name):
        return self.get_service(mock_name).get_http_requests()

    def clean_http_requests(self, mock_name):
        self.get_service(mock_name).clean_http_requests()

    def add_remote_return_value(self, mock_name, value):
        self.get_service(mock_name).add_remote_return_value(value)

    def get_remote_calls(self, mock_name):
        return self.get_service(mock_name).get_remote_calls()

    def clean_remote_calls(self, mock_name):
        self.get_service(mock_name).clean_remote_calls()

    async def publish(self, event_type, obj, reply_to=None, extra_headers=None):
        if extra_headers is None:
            extra_headers = {}
        if not self._setup:
            await self.messenger.setup()
            self._setup = True
        logging.info("Publishing message %s - %s", event_type, obj)
        try:
            await self.messenger.publish(event_type, obj, reply_to, extra_headers)
            logging.info("Message published successfully.")
        except Exception as e:
            logging.error("Error while publishing message: %s", e)
            raise

    async def call(
        self, service_name, method_name, *args, extra_headers=None, **kwargs
    ):
        if not self._setup:
            await self.messenger.setup()
            self._setup = True
        logging.info("Calling RPC %s.%s", service_name, method_name)
        try:
            if extra_headers is None:
                extra_headers = {}
            return await self.messenger.call(
                service_name, method_name, *args, extra_headers=extra_headers, **kwargs
            )
        except Exception as e:
            logging.error("Error while calling RPC: %s", e)
            raise

    def get_service(self, mock_name):
        if mock_name not in self.mocks:
            raise KeyError(
                f"Unknown mock service: {mock_name!r}. Known: {list(self.mocks)}"
            )
        _, service = self.mocks[mock_name]
        logging.info("Getting service %s: %s", mock_name, service)
        return service
