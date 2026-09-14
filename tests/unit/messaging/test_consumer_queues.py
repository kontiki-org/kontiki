from unittest.mock import AsyncMock, MagicMock

import pytest

from kontiki.messaging.consumer.core import Consumer
from kontiki.messaging.consumer.event import on_event
from kontiki.messaging.consumer.rpc import rpc


class DummyService:
    @rpc
    async def ping(self):
        return "ok"

    @on_event("plain_event")
    async def on_plain(self, payload):
        pass

    @on_event("catalog.changed", broadcast=True)
    async def on_broadcast(self, payload):
        pass

    @on_event("ui.progress", in_session=True)
    async def on_session(self, payload):
        pass


def _consumer():
    consumer = Consumer.__new__(Consumer)
    consumer.container = MagicMock()
    consumer.container.instance_id = "inst-1"
    consumer.container.service_instance = DummyService()
    consumer.container.config = {}
    consumer.service_name = "Svc"
    consumer.channel = MagicMock()
    consumer.channel.default_exchange = MagicMock()
    queue = MagicMock()
    queue.bind = AsyncMock()
    consumer.channel.declare_queue = AsyncMock(return_value=queue)
    consumer.rpc_exchange = MagicMock()
    consumer.event_exchange = MagicMock()
    consumer.serializer = MagicMock()
    consumer.rpc_tasks = []
    consumer.on_event_tasks = []
    return consumer


def _declare_kwargs(call):
    kwargs = dict(call.kwargs)
    if call.args:
        kwargs["name"] = call.args[0]
    return kwargs


def _declares(consumer):
    return [
        _declare_kwargs(call) for call in consumer.channel.declare_queue.await_args_list
    ]


@pytest.mark.asyncio
async def test_rpc_binds_shared_durable_and_instance_ephemeral_queues():
    consumer = _consumer()
    await consumer.add_rpc_tasks([DummyService.ping])

    declares = _declares(consumer)
    assert declares[0]["name"] == "Svc.ping.queue"
    assert declares[0].get("durable") is True
    assert "exclusive" not in declares[0]
    assert declares[1]["name"] == "Svc.ping.inst-1.queue"
    assert declares[1].get("exclusive") is True
    assert declares[1].get("auto_delete") is True
    assert declares[1].get("durable") is not True
    assert len(consumer.rpc_tasks) == 2


@pytest.mark.asyncio
async def test_competing_event_queue_is_durable():
    consumer = _consumer()
    await consumer.add_on_event_tasks([DummyService.on_plain])

    declares = _declares(consumer)
    assert declares == [{"name": "Svc.plain_event.queue", "durable": True}]


@pytest.mark.asyncio
async def test_broadcast_queue_is_ephemeral():
    consumer = _consumer()
    await consumer.add_on_event_tasks([DummyService.on_broadcast])

    declares = _declares(consumer)
    assert declares[0]["name"] == "Svc.catalog.changed.inst-1.queue"
    assert declares[0].get("exclusive") is True
    assert declares[0].get("auto_delete") is True
    assert declares[0].get("durable") is not True


@pytest.mark.asyncio
async def test_in_session_queue_is_ephemeral():
    consumer = _consumer()
    await consumer.add_on_event_tasks([DummyService.on_session])

    declares = _declares(consumer)
    assert declares[0]["name"] == "Svc.ui.progress.inst-1.queue"
    assert declares[0].get("exclusive") is True
    assert declares[0].get("auto_delete") is True
    assert declares[0].get("durable") is not True
