import json

from behave import then, when

from kontiki.messaging.publisher.rpc import RpcError
from runtime.registry_test_context import (
    capture_registry_test_exception_timestamp,
    resolve_placeholders,
)

REGISTRY_RPC_METHODS = frozenset(
    {
        "get_services",
        "get_exceptions",
        "get_events",
        "get_filtered_events",
        "get_filtered_exceptions",
    }
)


def _get_rpc_service(context, rpc_method):
    if getattr(context, "active_suite_tag", None) == "registry":
        if rpc_method in REGISTRY_RPC_METHODS:
            return "ServiceRegistry"
        return "RegistryTestService"
    return getattr(context, "rpc_service", "TestService")


@when("I call the {rpc_method} method with the following parameters")
def step_call_rpc_method(context, rpc_method):
    # Params passed as kwargs in all tests
    try:
        payload_str = context.text.strip() if context.text else ""
        params = json.loads(payload_str) if payload_str else {}
        placeholders = getattr(context, "registry_test_placeholders", None)
        if placeholders:
            params = resolve_placeholders(params, placeholders)
        service_name = _get_rpc_service(context, rpc_method)
        context.result = context.runner.call(service_name, rpc_method, **params)
        if (
            getattr(context, "active_suite_tag", None) == "registry"
            and rpc_method == "report_test_exception"
        ):
            capture_registry_test_exception_timestamp(context)
    except RpcError as e:
        context.code = e.code
        context.message = e.message
        context.result = None


@when("I call the {rpc_method} method with the following headers")
def step_call_rpc_method_with_headers(context, rpc_method):
    payload_str = context.text.strip() if context.text else ""
    params = json.loads(payload_str) if payload_str else {}
    headers = params.get("headers", params)

    try:
        context.result = context.runner.call(
            "TestService", rpc_method, extra_headers=headers
        )
    except RpcError as e:
        context.code = e.code
        context.message = e.message
        context.result = None


@then("the test service should return the result")
def step_return_result(context):
    assert context.result is not None
    assert context.result == context.text.strip()


@then("the test service should return the error")
def step_return_error(context):
    error_dict = json.loads(context.text.strip())
    assert context.code == error_dict["code"]
    assert context.message == error_dict["message"]
    assert context.result is None
