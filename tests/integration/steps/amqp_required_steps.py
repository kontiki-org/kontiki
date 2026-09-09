from behave import then, when
from runtime.process_manager import ServiceProcessManager

DATABASE_OPS_CLASS = "tests.integration.services.DatabaseOps"


def _stop_database_ops_service(context):
    manager = getattr(context, "amqp_required_manager", None)
    if manager is not None:
        manager.stop(timeout=5)
        context.amqp_required_manager = None


def start_database_ops_service(context, config_text, wait_until_up=True):
    _stop_database_ops_service(context)
    config_path = context.log_dir / "database_ops_service.yaml"
    config_path.write_text(config_text.strip() + "\n", encoding="utf-8")
    manager = ServiceProcessManager(
        name="DatabaseOps",
        service_class=DATABASE_OPS_CLASS,
        config_paths=[str(config_path)],
        log_dir=context.log_dir,
    )
    if wait_until_up:
        manager.start(timeout=20)
    else:
        try:
            manager.start(timeout=20, max_attempts=1)
        except (RuntimeError, TimeoutError):
            pass
    context.amqp_required_manager = manager


@when("I start a service with the following configuration")
def step_start_service_with_config(context):
    if not context.text or not context.text.strip():
        raise AssertionError("Configuration DocString is required.")
    start_database_ops_service(context, context.text, wait_until_up=False)


@then("the service is not running")
def step_service_is_not_running(context):
    manager = context.amqp_required_manager
    assert manager is not None, "No service was started."
    process = manager.process
    assert process is None or process.poll() is not None, (
        f"Expected service '{manager.name}' to have exited. "
        f"Check logs: {manager.log_file_path}"
    )
