import json
import time

from behave import given, then, when

from runtime.process_manager import ServiceProcessManager
from runtime.registry_test_context import (
    placeholders_from_registration,
    read_registration_from_log,
    resolve_placeholders,
)

HEARTBEAT_INTERVAL_SECONDS = 2
REGISTRY_TEST_CONFIG_PATHS = ["tests/integration/config_registry_test_service.yaml"]


def _stop_registry_test_service(context):
    if context.registry_test_manager is not None:
        context.registry_test_manager.stop(timeout=5)
        context.registry_test_manager = None


def _start_registry_test_service(context):
    _stop_registry_test_service(context)
    manager = ServiceProcessManager(
        name="RegistryTestService-1",
        service_class="tests.integration.services.RegistryTestService",
        config_paths=REGISTRY_TEST_CONFIG_PATHS,
        log_dir=context.log_dir,
    )
    manager.start(timeout=25)
    context.registry_test_manager = manager
    registration = read_registration_from_log(manager)
    context.registry_test_placeholders = placeholders_from_registration(registration)
    time.sleep(0.5)


@given("the registry service is running")
def step_registry_service_running(context):
    pass


@given("the registry test service is running")
def step_registry_test_service_running(context):
    _start_registry_test_service(context)


@when("I wait for the next registry heartbeat")
def step_wait_for_registry_heartbeat(context):
    time.sleep(HEARTBEAT_INTERVAL_SECONDS + 1)


@then("the registry service should return the result")
def step_registry_return_result(context):
    assert context.result is not None
    expected = resolve_placeholders(
        json.loads(context.text.strip()),
        context.registry_test_placeholders,
    )
    assert context.result == expected, (
        f"Expected:\n{json.dumps(expected, indent=2, ensure_ascii=True)}\n"
        f"Actual:\n{json.dumps(context.result, indent=2, ensure_ascii=True)}"
    )