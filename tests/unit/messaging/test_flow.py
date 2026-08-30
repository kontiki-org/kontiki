import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock

import pytest

from kontiki.messaging.flow import (
    FLOW_ID_LENGTH,
    FLOW_ID_UNSET,
    FlowIdFilter,
    apply_outbound_flow_id,
    current_flow_id,
    enter_flow_context,
    enter_flow_from_headers,
    flow_id_header_name,
    prepare_logging_config,
    reset_flow_id,
    resolve_flow_id,
)
from kontiki.messaging.publisher.messenger import Messenger
from kontiki.task.task import Task


@pytest.fixture(autouse=True)
def _clear_flow_id():
    token = enter_flow_context(None)
    yield
    reset_flow_id(token)


def test_resolve_generates_12_hex_and_sets_context():
    value = resolve_flow_id()
    assert len(value) == FLOW_ID_LENGTH
    assert all(c in "0123456789abcdef" for c in value)
    assert current_flow_id() == value


def test_resolve_explicit_flow_id_sets_context():
    value = resolve_flow_id(flow_id="my-business-id")
    assert value == "my-business-id"
    assert current_flow_id() == "my-business-id"


def test_resolve_reuses_context():
    first = resolve_flow_id()
    second = resolve_flow_id()
    assert first == second


def test_resolve_extra_headers_as_third_source():
    header = flow_id_header_name()
    value = resolve_flow_id(extra_headers={header: "from-extra-headers"})
    assert value == "from-extra-headers"
    assert current_flow_id() == "from-extra-headers"


def test_resolve_precedence_flow_id_over_context_and_header():
    header = flow_id_header_name()
    enter_flow_context("from-context")
    value = resolve_flow_id(
        flow_id="explicit",
        extra_headers={header: "from-header"},
    )
    assert value == "explicit"


def test_resolve_precedence_context_over_header():
    header = flow_id_header_name()
    enter_flow_context("from-context")
    value = resolve_flow_id(extra_headers={header: "from-header"})
    assert value == "from-context"


def test_apply_outbound_overwrites_header():
    header = flow_id_header_name()
    headers = {header: "stale"}
    apply_outbound_flow_id(headers, flow_id="fresh")
    assert headers[header] == "fresh"


@pytest.mark.asyncio
async def test_publish_sets_kontiki_flow_id_header():
    messenger = Messenger(standalone=True)
    messenger.serializer = MagicMock()
    messenger.serializer.dumps.return_value = b"{}"
    messenger.event_exchange = AsyncMock()
    messenger.container = None
    messenger.service_name = "test"
    messenger.instance_id = "inst"

    await messenger.publish("evt", {"a": 1})

    message = messenger.event_exchange.publish.await_args.args[0]
    flow = message.headers[flow_id_header_name()]
    assert len(flow) == FLOW_ID_LENGTH
    assert all(c in "0123456789abcdef" for c in flow)
    assert current_flow_id() == flow


@pytest.mark.asyncio
async def test_inbound_header_reused_on_child_publish():
    inbound_id = "a1b2c3d4e5f67890"
    token = enter_flow_from_headers({flow_id_header_name(): inbound_id})
    try:
        assert current_flow_id() == inbound_id

        messenger = Messenger(standalone=True)
        messenger.serializer = MagicMock()
        messenger.serializer.dumps.return_value = b"{}"
        messenger.event_exchange = AsyncMock()
        messenger.container = None
        messenger.service_name = "test"
        messenger.instance_id = "inst"

        await messenger.publish("child", {})
        message = messenger.event_exchange.publish.await_args.args[0]
        assert message.headers[flow_id_header_name()] == inbound_id
    finally:
        reset_flow_id(token)


@pytest.mark.asyncio
async def test_concurrent_handlers_isolate_flow_ids():
    results = {}

    async def handler(name, flow_id):
        token = enter_flow_from_headers({flow_id_header_name(): flow_id})
        try:
            await asyncio.sleep(0.01)
            results[name] = current_flow_id()
        finally:
            reset_flow_id(token)

    await asyncio.gather(
        handler("a", "aaaaaaaaaaaaaaaa"),
        handler("b", "bbbbbbbbbbbbbbbb"),
    )
    assert results["a"] == "aaaaaaaaaaaaaaaa"
    assert results["b"] == "bbbbbbbbbbbbbbbb"


@pytest.mark.asyncio
async def test_task_tick_resets_flow_between_invocations():
    seen = []

    async def user_task():
        assert current_flow_id() is not None
        seen.append(current_flow_id())

    task = Task(interval=0.01, user_task=user_task, immediate=True)
    await task._execute_user_task()
    await task._execute_user_task()

    assert len(seen) == 2
    assert seen[0] != seen[1]


def test_empty_context_filter_uses_no_flow():
    record = logging.LogRecord("n", logging.INFO, __file__, 1, "msg", (), None)
    assert FlowIdFilter().filter(record) is True
    assert record.flow_id == FLOW_ID_UNSET
    assert record.flow_id == "[no flow]"


def test_filter_uses_current_flow_id():
    enter_flow_context("0123456789ab")
    record = logging.LogRecord("n", logging.INFO, __file__, 1, "msg", (), None)
    FlowIdFilter().filter(record)
    assert record.flow_id == "[flow=0123456789ab]"


def test_filter_prevents_keyerror_in_format():
    record = logging.LogRecord("n", logging.INFO, __file__, 1, "hello", (), None)
    FlowIdFilter().filter(record)
    formatted = logging.Formatter("%(flow_id)s %(message)s").format(record)
    assert formatted == f"{FLOW_ID_UNSET} hello"


def test_prepare_logging_config_injects_filter_only():
    config = {
        "version": 1,
        "formatters": {"default": {"format": "%(message)s"}},
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
            }
        },
        "root": {"handlers": ["console"]},
    }
    prepared = prepare_logging_config(config)
    assert "kontiki_flow_id" in prepared["filters"]
    assert "kontiki_flow_id" in prepared["handlers"]["console"]["filters"]
    assert prepared["formatters"]["default"]["format"] == "%(message)s"
    # Original unchanged
    assert "filters" not in config


@pytest.mark.asyncio
async def test_sticky_flow_within_same_context_two_publishes():
    messenger = Messenger(standalone=True)
    messenger.serializer = MagicMock()
    messenger.serializer.dumps.return_value = b"{}"
    messenger.event_exchange = AsyncMock()
    messenger.container = None
    messenger.service_name = "test"
    messenger.instance_id = "inst"

    await messenger.publish("first", {})
    first = messenger.event_exchange.publish.await_args.args[0].headers[
        flow_id_header_name()
    ]
    await messenger.publish("second", {})
    second = messenger.event_exchange.publish.await_args.args[0].headers[
        flow_id_header_name()
    ]
    assert first == second
