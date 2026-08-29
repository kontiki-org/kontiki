import asyncio
import inspect
import logging.config
import os
import socket
import uuid

from kontiki.configuration.configuration import DEFAULT_LOGGING_CONFIGURATION
from kontiki.configuration.merge import merge
from kontiki.configuration.parameter import get_kontiki_parameter
from kontiki.delegate import ServiceDelegate
from kontiki.messaging.common import get_grace_seconds
from kontiki.messaging.consumer.core import Consumer
from kontiki.messaging.flow import prepare_logging_config
from kontiki.registry.client.heartbeat_publisher import HeartbeatPublisher
from kontiki.registry.client.registry_client import ServiceRegistryClient
from kontiki.task.task import Task, resolve_task_interval
from kontiki.utils import log
from kontiki.web.web import HttpServer

# -----------------------------------------------------------------------------


def resolve_service_name(service_cls, config):
    """Resolve logical service name: kontiki.service_name > class.name > class name."""
    default_name = service_cls.__name__
    for cls in service_cls.__mro__:
        if "name" in cls.__dict__:
            default_name = cls.__dict__["name"]
            break
    configured = get_kontiki_parameter(config, "service_name", None)
    if configured is None:
        return default_name
    if not isinstance(configured, str) or not configured:
        raise ValueError(
            "kontiki.service_name must be a non-empty string, " f"got {configured!r}"
        )
    return configured


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
        self.http_server = None
        self.instance_id = str(uuid.uuid4())
        self.pid = os.getpid()
        self.host = socket.gethostname()
        self.version = version

        self.config = {}
        self.delegates = {}
        self.tasks = []
        self.disable_service_registration = disable_service_registration
        self.shutting_down = False
        self._stop_started = False
        self.amqp_consumer = None

        self.service_registry_client = None
        if config_paths:
            self.config = self.load_config_files(config_paths)
        elif config:
            self.config = config
        else:
            log.error("No service configuration provided.")
            raise RuntimeError("No service configuration provided.")

        self.service_name = resolve_service_name(service_cls, self.config)

        logging_config = self.config.get("logging", DEFAULT_LOGGING_CONFIGURATION)
        logging.config.dictConfig(prepare_logging_config(logging_config))

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
            await self.amqp_consumer.setup()

            on_event_tasks = self.get_endpoints("on_event")
            await self.amqp_consumer.add_on_event_tasks(on_event_tasks)

            remote_tasks = self.get_endpoints("rpc")
            await self.amqp_consumer.add_rpc_tasks(remote_tasks)

    async def setup_delegates(self):
        for attr_name, delegate in self.get_delegates().items():
            delegate.bind(self, attr_name)
            log.debug("Binding %s and %s", self, attr_name)
            self.delegates[attr_name] = delegate
            setattr(self, attr_name, delegate)

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
        if self._amqp_ready():
            await self.amqp_consumer.start()

        await self.start_tasks()

        for delegate in self.delegates.values():
            await delegate.start()

    async def start_tasks(self):
        for attr_name in dir(self.service_instance):
            attr = getattr(self.service_instance, attr_name)
            if hasattr(attr, "_task_interval"):
                interval = resolve_task_interval(self.config, attr._task_interval)
                immediate = attr._task_immediate

                task = Task(interval, attr, immediate, container=self)
                log.debug("Starting %s task (interval=%s).", attr, interval)
                self.tasks.append(task)
                task.start()

    # --------------------------------------------------------------------------
    # Stop: stop accepting → drain in-flight → force close
    # --------------------------------------------------------------------------

    async def stop(self):
        if self._stop_started:
            return
        self._stop_started = True
        self.shutting_down = True  # blocks Messenger reconnect; gates AMQP prefetch

        grace_seconds = get_grace_seconds(self.config)

        # Stop accepting — no new work; unregister early so fleet sees us as gone
        log.info("Shutdown: stop accepting")
        await self._stop_accepting()

        # Drain in-flight — finish handlers already running (HTTP, AMQP, @task)
        log.info("Shutdown: draining in-flight work (grace_seconds=%s)", grace_seconds)
        try:
            await asyncio.wait_for(self._drain_in_flight(), timeout=grace_seconds)
            log.info("Shutdown: drain complete")
        except asyncio.TimeoutError:
            remaining = self._in_flight_summary()
            log.warning(
                "Shutdown: grace period exceeded, forcing close (%s)", remaining
            )

        # Force close — cancel remainder, close connections, stop delegates
        await self._force_close()
        log.info("Service stopped")

    async def _stop_accepting(self):
        if self.http_server:
            await self.http_server.stop_accepting()

        if self._amqp_ready():
            # cancel consumers; keep connection
            await self.amqp_consumer.stop_accepting()

        for task in self.tasks:
            task.stop_accepting()  # no new iteration after the current one

        # Heartbeat only: business delegates (Messenger, etc.) stay up during drain
        heartbeat = self.delegates.get("_kontiki_heartbeat")
        if heartbeat is not None:
            await heartbeat.stop()

        if self.service_registry_client:
            await self.service_registry_client.stop_accepting()
            await self.service_registry_client.unregister()

    async def _drain_in_flight(self):
        drain_tasks = []

        if self.http_server:
            drain_tasks.append(self.http_server.drain())

        if self._amqp_ready():
            drain_tasks.append(self.amqp_consumer.drain())

        for task in self.tasks:
            drain_tasks.append(task.drain())

        if drain_tasks:
            await asyncio.gather(*drain_tasks)

    async def _force_close(self):
        if self._amqp_ready():
            # nack+requeue prefetch not yet handled
            await self.amqp_consumer.force_close()

        for task in self.tasks:
            await task.force_stop()

        for attr_name in sorted(self.delegates.keys()):
            if attr_name == "_kontiki_heartbeat":
                continue
            await self.delegates[attr_name].stop()

        if self.service_registry_client:
            await self.service_registry_client.stop()

        if self.http_server:
            await self.http_server.drain()  # no-op if drain in-flight already ran

    def _amqp_ready(self):
        return (
            self.amqp_consumer is not None and self.amqp_consumer.connection is not None
        )

    def _in_flight_summary(self):
        parts = []
        if self._amqp_ready():
            parts.append(f"amqp_in_flight={self.amqp_consumer.work_in_flight.count}")
        return ", ".join(parts) if parts else "none"

    async def report_exception(self, exception, context=None):
        if context is None:
            context = {}

        if not self.service_registry_client:
            log.warning("Service registration is disabled or unavailable..")
            return

        try:
            await self.service_registry_client.register_exception(exception, context)
            log.debug("Exception published successfully: %s.", exception)
        except Exception as e:
            log.error("Error while publishing exception %s: %s", exception, e)

    async def report_uncaught_exception(self, exception, context):
        enabled = get_kontiki_parameter(
            self.config, "registration.report_uncaught_exceptions", True
        )
        if not enabled:
            return
        await self.report_exception(exception, context)

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
