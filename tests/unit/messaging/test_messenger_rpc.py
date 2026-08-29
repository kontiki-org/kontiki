from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aio_pika.exceptions import ChannelInvalidStateError

from kontiki.messaging.publisher.messenger import Messenger
from kontiki.messaging.publisher.rpc import RpcTimeoutError
from kontiki.messaging.rpc import RpcReturn


def _ready_messenger():
    messenger = Messenger(standalone=True)
    messenger._started = True
    messenger._rpc_timeout = 0.05
    messenger.serializer = MagicMock()
    messenger.serializer.dumps = MagicMock(return_value=b"{}")
    messenger.serializer.loads = MagicMock(return_value={"ok": True})
    messenger.callback_queue = MagicMock()
    messenger.callback_queue.name = "amq.callback"
    messenger.rpc_exchange = MagicMock()
    messenger.rpc_exchange.publish = AsyncMock()
    messenger.event_exchange = MagicMock()
    messenger.event_exchange.publish = AsyncMock()
    messenger.connection = AsyncMock()
    return messenger


def _incoming_message(correlation_id, body=b"{}"):
    message = MagicMock()
    message.correlation_id = correlation_id
    message.body = body

    @asynccontextmanager
    async def process():
        yield

    message.process = process
    return message


@pytest.mark.asyncio
async def test_on_response_acks_known_correlation_id():
    messenger = _ready_messenger()
    future = MagicMock()
    future.done.return_value = False
    messenger.futures["cid-1"] = future
    messenger.serializer.loads.return_value = "result"

    await messenger._on_response(_incoming_message("cid-1", b'"result"'))

    assert "cid-1" not in messenger.futures
    future.set_result.assert_called_once_with("result")


@pytest.mark.asyncio
async def test_on_response_acks_unknown_correlation_id():
    messenger = _ready_messenger()
    message = _incoming_message("unknown-cid")

    await messenger._on_response(message)

    # process() context manager exited without error → message was acked
    assert messenger.futures == {}


@pytest.mark.asyncio
async def test_reconnect_clears_started_and_recreates_setup():
    messenger = _ready_messenger()
    connection = messenger.connection
    messenger.setup = AsyncMock()

    await messenger.reconnect()

    connection.close.assert_awaited_once()
    messenger.setup.assert_awaited_once()
    assert messenger._reconnecting is False
    assert messenger._started is False
    assert messenger.connection is None


@pytest.mark.asyncio
async def test_reconnect_resets_started_before_setup():
    messenger = Messenger(standalone=True)
    messenger._started = True
    messenger.connection = AsyncMock()
    observed = {}

    async def fake_setup():
        observed["started_during_setup"] = messenger._started
        messenger._started = True

    messenger.setup = fake_setup

    await messenger.reconnect()

    assert observed["started_during_setup"] is False
    assert messenger._started is True
    assert messenger.callback_queue is None
    assert messenger._callback_consumer_tag is None


@pytest.mark.asyncio
async def test_call_retries_after_channel_invalid_state():
    messenger = _ready_messenger()
    messenger._rpc_timeout = 1.0

    publish = messenger.rpc_exchange.publish
    publish.side_effect = [ChannelInvalidStateError(), None]

    async def fake_reconnect():
        cid = next(iter(messenger.futures))
        messenger.futures[cid].set_result(RpcReturn(success=True, result="ok"))

    with patch.object(messenger, "reconnect", side_effect=fake_reconnect):
        result = await messenger.call("Svc", "method")

    assert result == "ok"
    assert publish.await_count == 2


@pytest.mark.asyncio
async def test_call_timeout_removes_future_and_late_response_is_acked():
    messenger = _ready_messenger()
    messenger._rpc_timeout = 0.01

    with pytest.raises(RpcTimeoutError):
        await messenger.call("Svc", "slow")

    assert messenger.futures == {}

    # Late reply for the timed-out call must still be acked
    await messenger._on_response(_incoming_message("stale-cid"))
