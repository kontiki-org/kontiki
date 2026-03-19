import inspect
import logging.config
import os
import socket
import uuid

from kontiki.configuration.configuration import DEFAULT_LOGGING_CONFIGURATION
from kontiki.configuration.merge import merge
from kontiki.configuration.parameter import get_kontiki_parameter
from kontiki.delegate import ServiceDelegate
from kontiki.messaging.consumer.core import Consumer
from kontiki.registry.client.heartbeat_publisher import HeartbeatPublisher
from kontiki.registry.client.registry_client import ServiceRegistryClient
from kontiki.task.task import Task
from kontiki.utils import log
from kontiki.web.web import HttpServer

# -----------------------------------------------------------------------------


class ServiceContainer:
    def __init__(
        self,
        service_cls,
        version,
        config_paths,
        disable_service_registration,
        config=None,
    ):
        self.service_cls = service_cls
        self.service_instance = service_cls()
        self.service_name = (
            service_cls.name
            if hasattr(service_cls, "name")
            else self.service_instance.__class__.__name__
        )
        self.http_server = None
        # Unique ID for each instance of the service
        self.instance_id = str(uuid.uuid4())
        self.pid = os.getpid()
        self.host = socket.gethostname()
        self.version = version

        self.config = {}
        self.delegates = {}
        self.tasks = []
        self.disable_service_registration = disable_service_registration

        self.service_registry_client = None
        if config_paths:
            self.config = self.load_config_files(config_paths)
        elif config:
            self.config = config
        else:
            log.error("No service configuration provided.")
            raise RuntimeError("No service configuration provided.")

        # Initialize logging system
        logging_config = self.config.get("logging", DEFAULT_LOGGING_CONFIGURATION)
        logging.config.dictConfig(logging_config)

    def load_config_files(self, conf_files):
        try:
            conf = merge(conf_files)
            log.info("Configurations loaded from: %s", conf_files)
            return conf
        except RuntimeError as e:
            log.error("Error loading configurations: %s", e)
            raise e

    # --------------------------------------------------------------------------
    # Setup
    # --------------------------------------------------------------------------

    async def setup(self):
        # Inject configuration into the service
        if hasattr(self.service_instance, "config"):
            self.service_instance.config = self.config

        self.amqp_consumer = Consumer(self)

        await self.setup_service_registry()
        await self.setup_http_endpoints()
        await self.setup_amqp_endpoints()
        await self.setup_delegates()

        log.info("Service setup completed")

    async def setup_http_endpoints(self):
        if self.has_endpoints("http"):
            http_endpoints = self.get_endpoints("http")
            self.http_server = HttpServer(self, http_endpoints)
            await self.http_server.setup()

    async def setup_amqp_endpoints(self):
        if self.has_endpoints("on_event") or self.has_endpoints("rpc"):
            # Setup AMQP consumer
            await self.amqp_consumer.setup()

            # Setup on_event endpoints
            on_event_tasks = self.get_endpoints("on_event")
            await self.amqp_consumer.add_on_event_tasks(on_event_tasks)

            # Setup rpc endpoints
            remote_tasks = self.get_endpoints("rpc")
            await self.amqp_consumer.add_rpc_tasks(remote_tasks)

    async def setup_delegates(self):
        # Bind delegates
        for attr_name, delegate in self.get_delegates().items():
            delegate.bind(self, attr_name)
            log.debug("Binding %s and %s", self, attr_name)
            self.delegates[attr_name] = delegate
            setattr(self, attr_name, delegate)

        # Setup delegates
        for delegate in self.delegates.values():
            await delegate.setup()

    async def setup_service_registry(self):
        self.disable_service_registration = get_kontiki_parameter(
            self.config, "registration.disable", self.disable_service_registration
        )
        if self.disable_service_registration:
            return
        self.service_registry_client = ServiceRegistryClient(self)
        await self.service_registry_client.setup()

    # --------------------------------------------------------------------------
    # Start
    # --------------------------------------------------------------------------

    async def start(self):
        if self.http_server is not None:
            await self.http_server.start()
        if self.amqp_consumer is not None:
            await self.amqp_consumer.start()

        await self.start_tasks()

        for delegate in self.delegates.values():
            await delegate.start()

    async def start_tasks(self):
        for attr_name in dir(self.service_instance):
            attr = getattr(self.service_instance, attr_name)
            if hasattr(attr, "_task_interval"):
                interval = getattr(attr, "_task_interval")
                immediate = getattr(attr, "_task_immediate", True)

                task = Task(interval, attr, immediate)
                log.debug("Starting %s task.", attr)
                self.tasks.append(task)
                task.start()

    # --------------------------------------------------------------------------
    # Stop
    # --------------------------------------------------------------------------

    async def stop(self):
        log.info("Stopping the service...")
        for delegate in self.delegates.values():
            await delegate.stop()

        for task in self.tasks:
            task.stop()

        if self.http_server:
            await self.http_server.stop()

        if self.service_registry_client:
            await self.service_registry_client.unregister()
            await self.service_registry_client.stop()
        if self.amqp_consumer:
            await self.amqp_consumer.stop()

    # Internal methods

    def get_endpoints(self, type_):
        endpoints = []
        for name, method in inspect.getmembers(
            self.service_cls, predicate=inspect.isfunction
        ):
            if hasattr(method, f"_{type_}_endpoint"):
                log.debug("Discovered %s entrypoint: %s", type_, name)
                endpoints.append(method)
        return endpoints

    def has_endpoints(self, type_):
        for _, method in inspect.getmembers(
            self.service_cls, predicate=inspect.isfunction
        ):
            if hasattr(method, f"_{type_}_endpoint"):
                return True
        return False

    def get_delegates(self):
        delegates = self._get_internal_delegates()
        for attr_name, value in inspect.getmembers(self.service_cls):
            if isinstance(value, ServiceDelegate):
                delegates[attr_name] = value
        return delegates

    def _get_internal_delegates(self):
        delegates = {}
        delegates["_kontiki_heartbeat"] = HeartbeatPublisher(
            self.service_registry_client
        )
        return delegates
