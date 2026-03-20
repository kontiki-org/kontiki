from pathlib import Path

from runtime.process_manager import ServiceProcessManager

from kontiki.messaging import on_event
from kontiki.testing import MockService, MockServiceManager, MockServiceRunner

LOG_DIR = Path("logs/integration")


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


def before_all(context):
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    context.service_manager = ServiceProcessManager(
        name="TestService",
        service_class="tests.integration.service.TestService",
        config_paths=["tests/integration/config.yaml"],
        log_dir=LOG_DIR,
    )
    context.service_manager.start(timeout=20)

    # Setup and start the mock service manager and runner
    context.manager = MockServiceManager(log_file=str(LOG_DIR / "mock_services.log"))
    context.manager.add(
        TestMockService,
        config={"kontiki": {"amqp": {"url": "amqp://guest:guest@localhost/"}}},
    )
    context.runner = MockServiceRunner(context.manager)
    context.runner.start()
    context.runner.ready_event.wait(timeout=10)


def after_all(context):
    if context.runner is not None:
        context.runner.stop()
    if context.service_manager is not None:
        context.service_manager.stop()
