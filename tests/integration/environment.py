from pathlib import Path

from runtime.process_manager import ServiceProcessManager

from kontiki.messaging import on_event
from kontiki.testing import MockService, MockServiceManager, MockServiceRunner
from kontiki.testing.delegates.event_manager import EventManager

LOG_DIR = Path("logs/integration")
SERVICE_DEFINITIONS_BY_TAG = {
    "single_instance": [
        {
            "name": "TestService-1",
            "service_class": "tests.integration.services.TestService",
            "config_paths": ["tests/integration/config.yaml"],
        }
    ],
    "multi_instance": [
        {
            "name": "TestService-1",
            "service_class": "tests.integration.services.TestService",
            "config_paths": [
                "tests/integration/config.yaml",
                "tests/integration/config_multi_1.yaml",
            ],
        },
        {
            "name": "TestService-2",
            "service_class": "tests.integration.services.TestService",
            "config_paths": [
                "tests/integration/config.yaml",
                "tests/integration/config_multi_2.yaml",
            ],
        },
    ],
    "task_service": [
        {
            "name": "TaskService",
            "service_class": "tests.integration.services.TaskService",
            "config_paths": ["tests/integration/config.yaml"],
        },
    ],
    "task_config_service": [
        {
            "name": "TaskConfigService",
            "service_class": "tests.integration.services.TaskConfigService",
            "config_paths": ["tests/integration/config.yaml"],
        },
    ],
    # Registry process is started from the feature Given DocString
    # (see registry_steps), not from this map.
    "registry": [],
}
EXCLUSIVE_SUITE_TAGS = list(SERVICE_DEFINITIONS_BY_TAG.keys())


class TestMockService(MockService):
    @on_event("simple_event_processed")
    async def on_simple_event_processed(self, payload):
        self.event_manager.store_event(payload)

    @on_event("dynamic_event_name_processed")
    async def on_dynamic_event_name_processed(self, payload):
        self.event_manager.store_event(payload)

    @on_event("retry_ok_processed")
    async def on_retry_ok_processed(self, payload):
        self.event_manager.store_event(payload)

    @on_event("broadcast_off_processed")
    async def on_broadcast_off_processed(self, payload):
        self.event_manager.store_event(payload)

    @on_event("broadcast_on_processed")
    async def on_broadcast_on_processed(self, payload):
        self.event_manager.store_event(payload)


class TaskMockService(MockService):
    @on_event("task_immediate_processed")
    async def on_task_immediate_processed(self, payload):
        self.event_manager.store_event(payload)

    @on_event("task_not_immediate_processed")
    async def on_task_not_immediate_processed(self, payload):
        self.event_manager.store_event(payload)

    @on_event("task_from_config_processed")
    async def on_task_from_config_processed(self, payload):
        self.event_manager.store_event(payload)


class RegistryEventListener(MockService):
    name = "RegistryEventListener"
    event_manager = EventManager()

    @on_event("registry.instance.registered")
    async def on_instance_registered(self, payload):
        self.event_manager.store_event(payload)

    @on_event("registry.instance.deregistered")
    async def on_instance_deregistered(self, payload):
        self.event_manager.store_event(payload)

    @on_event("registry.instance.status_changed")
    async def on_instance_status_changed(self, payload):
        self.event_manager.store_event(payload)

    @on_event("registry.exception.recorded")
    async def on_exception_recorded(self, payload):
        self.event_manager.store_event(payload)


def before_all(context):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    context.log_dir = LOG_DIR
    context.service_managers = []
    context.active_suite_tag = None
    context.registry_test_manager = None
    # Mutable bag on the root context layer so the registry process
    # handle survives Behave's per-scenario context pop.
    context.registry = {"manager": None, "config_text": None}

    # Setup and start the mock service manager and runner
    context.manager = MockServiceManager(log_file=str(LOG_DIR / "mock_services.log"))
    config = {"kontiki": {"amqp": {"url": "amqp://guest:guest@localhost/"}}}
    context.manager.add(TestMockService, config)
    context.manager.add(TaskMockService, config)
    context.manager.add(RegistryEventListener, config)
    context.runner = MockServiceRunner(context.manager)
    context.runner.start()
    context.runner.ready_event.wait(timeout=10)


def before_tag(context, tag):
    if tag not in EXCLUSIVE_SUITE_TAGS:
        return

    _start_test_suite(context, tag)


def before_scenario(context, scenario):
    if context.active_suite_tag is None:
        raise RuntimeError("No test suite has been started")

    if context.active_suite_tag == "registry":
        context.manager.get_service("RegistryEventListener").clean_events()


def after_scenario(context, scenario):
    if context.registry_test_manager is not None:
        context.registry_test_manager.stop(timeout=5)
        context.registry_test_manager = None


def _start_test_suite(context, suite_tag):
    if context.active_suite_tag is None:
        context.active_suite_tag = suite_tag
    elif context.active_suite_tag != suite_tag:
        # First started suite keeps priority; ignore other suite tags.
        return

    if context.service_managers:
        return

    for service in SERVICE_DEFINITIONS_BY_TAG[suite_tag]:
        manager = ServiceProcessManager(
            name=service["name"],
            service_class=service["service_class"],
            config_paths=service["config_paths"],
            log_dir=LOG_DIR,
        )
        manager.start(timeout=20)
        context.service_managers.append(manager)


def after_all(context):
    if context.runner is not None:
        context.runner.stop()
    manager = context.registry["manager"]
    if manager is not None:
        manager.stop(timeout=5)
        context.registry["manager"] = None
        context.registry["config_text"] = None
    for manager in reversed(context.service_managers):
        manager.stop(timeout=5)
