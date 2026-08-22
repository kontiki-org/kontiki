import json

from behave import given, then, when
from runtime.process_manager import ServiceProcessManager

from kontiki.messaging.publisher.rpc import RpcError

SERVICE_NAME_TEST_CLASS = "tests.integration.services.ServiceNameTestService"
RPC_PROXY_CALLER_CLASS = "tests.integration.services.RpcProxyCallerService"


def _stop_service_name_service(context):
    if context.service_name_manager is not None:
        context.service_name_manager.stop(timeout=5)
        context.service_name_manager = None


def _stop_rpc_proxy_caller(context):
    if context.rpc_proxy_caller_manager is not None:
        context.rpc_proxy_caller_manager.stop(timeout=5)
        context.rpc_proxy_caller_manager = None


@given("a service is running with the following configuration")
def step_service_running_with_config(context):
    if not context.text or not context.text.strip():
        raise AssertionError("Configuration DocString is required.")
    _stop_service_name_service(context)
    config_path = context.log_dir / "service_name_service.yaml"
    config_path.write_text(context.text.strip() + "\n", encoding="utf-8")
    manager = ServiceProcessManager(
        name="ServiceNameOverride",
        service_class=SERVICE_NAME_TEST_CLASS,
        config_paths=[str(config_path)],
        log_dir=context.log_dir,
    )
    manager.start(timeout=20)
    context.service_name_manager = manager


@given("a caller service is running with the following configuration")
def step_caller_service_running_with_config(context):
    if not context.text or not context.text.strip():
        raise AssertionError("Configuration DocString is required.")
    _stop_rpc_proxy_caller(context)
    config_path = context.log_dir / "rpc_proxy_caller_service.yaml"
    config_path.write_text(context.text.strip() + "\n", encoding="utf-8")
    manager = ServiceProcessManager(
        name="RpcProxyCaller",
        service_class=RPC_PROXY_CALLER_CLASS,
        config_paths=[str(config_path)],
        log_dir=context.log_dir,
    )
    manager.start(timeout=20)
    context.rpc_proxy_caller_manager = manager


@when(
    "I call the {rpc_method} method of {service_name} with the following parameters"
)
def step_call_rpc_of_service(context, rpc_method, service_name):
    payload_str = context.text.strip() if context.text else ""
    params = json.loads(payload_str) if payload_str else {}
    try:
        context.result = context.runner.call(service_name, rpc_method, **params)
    except RpcError as e:
        context.code = e.code
        context.message = e.message
        context.result = None


@then("{service_name} should return the result")
def step_named_service_return_result(context, service_name):
    assert context.result is not None, (
        f"Expected a result from {service_name}, got None "
        f"(code={getattr(context, 'code', None)}, "
        f"message={getattr(context, 'message', None)})"
    )
    assert context.result == context.text.strip()
