from behave import given
from runtime.process_manager import ServiceProcessManager

TEST_SERVICE_CLASS = "tests.integration.services.TestService"


def _stop_http_disable_service(context):
    if context.http_disable_manager is not None:
        context.http_disable_manager.stop(timeout=5)
        context.http_disable_manager = None


@given("the test service is running with the following configuration")
def step_test_service_running_with_config(context):
    if not context.text or not context.text.strip():
        raise AssertionError("Configuration DocString is required.")
    _stop_http_disable_service(context)
    config_path = context.log_dir / "http_disable_service.yaml"
    config_path.write_text(context.text.strip() + "\n", encoding="utf-8")
    manager = ServiceProcessManager(
        name="HttpDisableTestService",
        service_class=TEST_SERVICE_CLASS,
        config_paths=[str(config_path)],
        log_dir=context.log_dir,
    )
    manager.start(timeout=20)
    context.http_disable_manager = manager
