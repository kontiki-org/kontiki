import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp import web

from kontiki.messaging.consumer.core import WorkInFlight
from kontiki.messaging.consumer.event import OnEventTask
from kontiki.messaging.flow import (
    current_flow_id,
    enter_flow_context,
    flow_id_header_name,
    reset_flow_id,
    resolve_flow_id,
)
from kontiki.runtime.handler_scope import (
    FLOW_ID_LENGTH,
    HOP_ID_LENGTH,
    apply_outbound_hop_headers,
    current_handler_context,
    enter_handler_scope,
    entrypoint_header_name,
    exception_record_fields,
    hop_id_header_name,
    operation_header_name,
    parent_hop_id_header_name,
    reset_handler_scope,
    rpc_service_header_name,
)
from kontiki.web.web import prepare_http_response


@pytest.fixture(autouse=True)
def _clear_handler_context():
    token = enter_flow_context(None)
    yield
    reset_flow_id(token)


def _hex_flow_id(value):
    assert len(value) == FLOW_ID_LENGTH
    assert all(c in "0123456789abcdef" for c in value)


def test_http_scope_generates_flow_id_and_context():
    scope = enter_handler_scope("http", "GET /api/foo")
    try:
        ctx = current_handler_context()
        assert ctx.kind == "http"
        assert ctx.operation == "GET /api/foo"
        _hex_flow_id(ctx.flow_id)
        assert current_flow_id() == ctx.flow_id
    finally:
        reset_handler_scope(scope)

    assert current_handler_context() is None
    assert current_flow_id() is None


def test_task_scope_generates_flow_id_at_entry():
    scope = enter_handler_scope("task", "cleanup_tick")
    try:
        ctx = current_handler_context()
        assert ctx.kind == "task"
        assert ctx.operation == "cleanup_tick"
        _hex_flow_id(ctx.flow_id)
    finally:
        reset_handler_scope(scope)


def test_rpc_scope_reuses_inbound_flow_header():
    inbound = "a1b2c3d4e5f6"
    scope = enter_handler_scope(
        "rpc",
        "my_method",
        headers={flow_id_header_name(): inbound},
    )
    try:
        ctx = current_handler_context()
        assert ctx.kind == "rpc"
        assert ctx.flow_id == inbound
    finally:
        reset_handler_scope(scope)


def test_event_scope_without_header_generates_flow_id_at_entry():
    scope = enter_handler_scope("event", "alert.normalized", headers={})
    try:
        generated = current_handler_context().flow_id
        _hex_flow_id(generated)
        assert current_flow_id() == generated
    finally:
        reset_handler_scope(scope)


def test_rpc_scope_without_header_generates_flow_id_at_entry():
    scope = enter_handler_scope("rpc", "my_method")
    try:
        _hex_flow_id(current_handler_context().flow_id)
    finally:
        reset_handler_scope(scope)


def test_flow_only_context_has_no_handler_context():
    resolve_flow_id()
    assert current_flow_id() is not None
    assert current_handler_context() is None
    assert exception_record_fields() == (None, None, None, None)


def test_exception_record_fields_by_kind():
    cases = [
        ("rpc", "compute"),
        ("event", "alert.open"),
        ("http", "POST /submit"),
        ("task", "poll_source"),
    ]
    for kind, operation in cases:
        scope = enter_handler_scope(kind, operation)
        try:
            flow_id, entrypoint, recorded_operation, hop_id = exception_record_fields()
            ctx = current_handler_context()
            assert entrypoint == kind
            assert recorded_operation == operation
            assert flow_id == ctx.flow_id
            assert hop_id is None
        finally:
            reset_handler_scope(scope)

    assert exception_record_fields() == (None, None, None, None)


def test_scope_calls_work_in_flight_begin_and_end():
    work = WorkInFlight()
    scope = enter_handler_scope("rpc", "m", work_in_flight=work)
    assert work.count == 1
    reset_handler_scope(scope)
    assert work.count == 0


def test_prepare_http_response_sets_kontiki_flow_id_header():
    response = web.Response()
    prepare_http_response(response, "abc123def456")
    assert response.headers[flow_id_header_name()] == "abc123def456"


def test_prepare_http_response_skips_header_when_flow_id_is_none():
    response = web.Response()
    prepare_http_response(response, None)
    assert flow_id_header_name() not in response.headers


@pytest.mark.asyncio
async def test_concurrent_handler_scopes_isolate_context():
    results = {}

    async def run(kind, operation, flow_id):
        headers = {flow_id_header_name(): flow_id} if flow_id else None
        scope = enter_handler_scope(kind, operation, headers=headers)
        try:
            await asyncio.sleep(0.01)
            ctx = current_handler_context()
            results[operation] = (ctx.kind, ctx.flow_id)
        finally:
            reset_handler_scope(scope)

    await asyncio.gather(
        run("rpc", "a", "aaaaaaaaaaaa"),
        run("event", "b", "bbbbbbbbbbbb"),
        run("http", "GET /c", None),
    )

    assert results["a"] == ("rpc", "aaaaaaaaaaaa")
    assert results["b"] == ("event", "bbbbbbbbbbbb")
    _hex_flow_id(results["GET /c"][1])


@pytest.mark.asyncio
async def test_event_handler_reports_uncaught_exception():
    container = MagicMock()
    container.amqp_consumer.work_in_flight = WorkInFlight()
    container.report_uncaught_exception = AsyncMock()

    async def failing_handler(_payload):
        raise RuntimeError("event blew up")

    message = MagicMock()
    message.headers = {}
    message.redelivered = False
    message.body = b"{}"
    message.process = MagicMock()
    message.process.return_value.__aenter__ = AsyncMock(return_value=None)
    message.process.return_value.__aexit__ = AsyncMock(return_value=False)
    message.nack = AsyncMock()

    serializer = MagicMock()
    serializer.loads.return_value = {"x": 1}

    task = OnEventTask(
        event_type="tests.fail",
        task=failing_handler,
        queue=MagicMock(),
        serializer=serializer,
        include_headers=False,
        requeue_on_error=False,
        reject_on_redelivered=False,
        container=container,
    )

    await task._consume_message(message)

    container.report_uncaught_exception.assert_awaited_once()
    (exc,) = container.report_uncaught_exception.await_args.args
    assert isinstance(exc, RuntimeError)
    assert str(exc) == "event blew up"
    assert container.report_uncaught_exception.await_args.kwargs == {}
    message.nack.assert_awaited_once_with(requeue=False)


def _hex_hop_id(value):
    assert len(value) == HOP_ID_LENGTH
    assert all(c in "0123456789abcdef" for c in value)


def test_rpc_scope_remembers_inbound_hop_id():
    inbound_hop = "aabbccddeeff0011"
    scope = enter_handler_scope(
        "rpc",
        "my_method",
        headers={hop_id_header_name(): inbound_hop},
    )
    try:
        assert current_handler_context().hop_id == inbound_hop
        _, _, _, hop_id = exception_record_fields()
        assert hop_id == inbound_hop
    finally:
        reset_handler_scope(scope)


def test_http_scope_ignores_inbound_hop_header():
    scope = enter_handler_scope(
        "http",
        "GET /alerts",
        headers={hop_id_header_name(): "aabbccddeeff0011"},
    )
    try:
        assert current_handler_context().hop_id is None
        _, _, _, hop_id = exception_record_fields()
        assert hop_id is None
    finally:
        reset_handler_scope(scope)


def test_outbound_outside_handler_has_hop_id_and_omits_parent():
    headers = {}
    apply_outbound_hop_headers(headers)
    _hex_hop_id(headers[hop_id_header_name()])
    assert parent_hop_id_header_name() not in headers
    assert entrypoint_header_name() not in headers
    assert operation_header_name() not in headers
    assert rpc_service_header_name() not in headers


def test_http_outbound_omits_parent_and_stamps_entrypoint():
    scope = enter_handler_scope("http", "GET /alerts")
    try:
        headers = {}
        apply_outbound_hop_headers(headers)
        _hex_hop_id(headers[hop_id_header_name()])
        assert parent_hop_id_header_name() not in headers
        assert headers[entrypoint_header_name()] == "http"
        assert headers[operation_header_name()] == "GET /alerts"
    finally:
        reset_handler_scope(scope)


def test_rpc_outbounds_share_inbound_parent_and_get_distinct_hop_ids():
    inbound_hop = "aabbccddeeff0011"
    scope = enter_handler_scope(
        "rpc",
        "charge",
        headers={hop_id_header_name(): inbound_hop},
    )
    try:
        first = {}
        second = {}
        apply_outbound_hop_headers(first)
        apply_outbound_hop_headers(second, rpc_service="billing")
        third = {}
        apply_outbound_hop_headers(third)
        parent_key = parent_hop_id_header_name()
        hop_key = hop_id_header_name()
        assert first[parent_key] == inbound_hop
        assert second[parent_key] == inbound_hop
        assert third[parent_key] == inbound_hop
        assert len({first[hop_key], second[hop_key], third[hop_key]}) == 3
        assert current_handler_context().hop_id == inbound_hop
        assert first[entrypoint_header_name()] == "rpc"
        assert first[operation_header_name()] == "charge"
        assert rpc_service_header_name() not in first
        assert second[rpc_service_header_name()] == "billing"
        assert rpc_service_header_name() not in third
    finally:
        reset_handler_scope(scope)
