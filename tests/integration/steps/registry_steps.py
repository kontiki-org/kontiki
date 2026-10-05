import asyncio
import json
import time

from aio_pika import connect_robust
from behave import given, step, then, when

from kontiki.messaging.common import (
    AMQP_DEFAULT_URL,
    FAILED_QUEUE_MAX_LENGTH,
    failed_queue_name,
)
from kontiki.messaging.publisher.rpc import RpcError
from runtime.process_manager import ServiceProcessManager
from runtime.registry_test_context import (
    matches_with_timestamps,
    placeholders_from_registration,
    read_registration_from_log,
    resolve_placeholders,
    wait_for_registry_event,
)

HEARTBEAT_INTERVAL_SECONDS = 2
REGISTRY_SERVICE_CLASS = "kontiki.registry.server.service.ServiceRegistry"
REGISTRY_TEST_SERVICE_CLASS = "tests.integration.services.RegistryTestService"
REGISTRY_UNCAUGHT_TASK_SERVICE_CLASS = (
    "tests.integration.services.RegistryUncaughtTaskTestService"
)
FAILED_REPLAY_SERVICE_CLASS = "tests.integration.services.FailedReplayService"
FAILED_LIST_WAIT_SECONDS = 10


def _registry_test_service_class(context):
    tags = context.scenario.effective_tags
    if "failed_replay" in tags:
        return FAILED_REPLAY_SERVICE_CLASS
    if "uncaught_task" in tags:
        return REGISTRY_UNCAUGHT_TASK_SERVICE_CLASS
    return REGISTRY_TEST_SERVICE_CLASS


def _stop_registry_service(context):
    manager = context.registry["manager"]
    if manager is not None:
        manager.stop(timeout=5)
        context.registry["manager"] = None
        context.registry["config_text"] = None


def _start_registry_service(context, config_text):
    normalized = config_text.strip()
    _stop_registry_service(context)
    config_path = context.log_dir / "registry_service.yaml"
    config_path.write_text(normalized + "\n", encoding="utf-8")
    manager = ServiceProcessManager(
        name="ServiceRegistry",
        service_class=REGISTRY_SERVICE_CLASS,
        config_paths=[str(config_path)],
        log_dir=context.log_dir,
    )
    manager.start(timeout=25)
    context.registry["manager"] = manager
    context.registry["config_text"] = normalized


def _stop_registry_test_service(context):
    if context.registry_test_manager is not None:
        context.registry_test_manager.stop(timeout=5)
        context.registry_test_manager = None


def _purge_failed_replay_queue():
    async def _purge():
        connection = await connect_robust(AMQP_DEFAULT_URL)
        try:
            channel = await connection.channel()
            queue = await channel.declare_queue(
                failed_queue_name("FailedReplayService", "job.run"),
                durable=True,
                arguments={
                    "x-queue-type": "quorum",
                    "x-max-length": FAILED_QUEUE_MAX_LENGTH,
                    "x-overflow": "reject-publish",
                },
            )
            await queue.purge()
        finally:
            await connection.close()

    asyncio.run(_purge())


def _start_registry_test_service(context, config_text):
    _stop_registry_test_service(context)
    if _registry_test_service_class(context) == FAILED_REPLAY_SERVICE_CLASS:
        _purge_failed_replay_queue()
    config_path = context.log_dir / "registry_test_service.yaml"
    config_path.write_text(config_text.strip() + "\n", encoding="utf-8")
    manager = ServiceProcessManager(
        name="RegistryTestService-1",
        service_class=_registry_test_service_class(context),
        config_paths=[str(config_path)],
        log_dir=context.log_dir,
    )
    manager.start(timeout=25)
    context.registry_test_manager = manager
    registration = read_registration_from_log(manager)
    context.registry_test_placeholders = placeholders_from_registration(registration)
    time.sleep(0.5)


@given("the registry service is running with the following configuration")
def step_registry_service_running_with_config(context):
    if not context.text or not context.text.strip():
        raise AssertionError("Registry service configuration DocString is required.")
    _start_registry_service(context, context.text)


@given("the registry test service is running with the following configuration")
@when("the registry test service is running with the following configuration")
def step_registry_test_service_running_with_config(context):
    if not context.text or not context.text.strip():
        raise AssertionError(
            "Registry test service configuration DocString is required."
        )
    _start_registry_test_service(context, context.text)


@when("I stop the registry test service")
def step_stop_registry_test_service(context):
    _stop_registry_test_service(context)


@when("I kill the registry test service without unregistering")
def step_kill_registry_test_service(context):
    if context.registry_test_manager is None:
        raise AssertionError("Registry test service is not running.")
    context.registry_test_manager.kill()
    context.registry_test_manager = None


@step("I wait for the next registry heartbeat")
def step_wait_for_registry_heartbeat(context):
    time.sleep(HEARTBEAT_INTERVAL_SECONDS + 1)


@then("the registry should publish the {event_type} event with the following payload")
def step_registry_published_event(context, event_type):
    expected = json.loads(context.text.strip())
    wait_for_registry_event(context, expected)


def _repeat_last_rpc(context):
    try:
        context.result = context.runner.call(
            context.rpc_service_name, context.rpc_method, **context.rpc_params
        )
        context.code = None
        context.message = None
    except RpcError as exc:
        context.code = exc.code
        context.message = exc.message
        context.result = None


@then("the registry service should return the result")
def step_registry_return_result(context):
    placeholders = context.registry_test_placeholders or {}
    expected = resolve_placeholders(
        json.loads(context.text.strip()),
        placeholders,
    )
    if context.rpc_method == "list_failed_messages":
        deadline = time.time() + FAILED_LIST_WAIT_SECONDS
        while context.result is None or not matches_with_timestamps(
            context.result, expected
        ):
            if time.time() >= deadline:
                break
            time.sleep(0.2)
            _repeat_last_rpc(context)
    assert context.result is not None
    assert matches_with_timestamps(context.result, expected), (
        f"Expected:\n{json.dumps(expected, indent=2, ensure_ascii=True)}\n"
        f"Actual:\n{json.dumps(context.result, indent=2, ensure_ascii=True)}"
    )
