from unittest.mock import AsyncMock

import pytest

from kontiki.messaging.publisher.session import EventSession


@pytest.mark.asyncio
async def test_event_session_publish_builds_routing_key_and_headers():
    messenger = AsyncMock()
    session = EventSession(
        messenger, service_name="ServiceA", instance_id="inst-1", session_id="sess-42"
    )

    payload = {"foo": "bar"}
    extra = {"x-header": "value"}

    await session.publish("my_event", payload, extra_headers=extra)

    messenger.publish.assert_awaited_once()
    call = messenger.publish.call_args
    event_type, obj = call.args

    # Routing key must be suffixed with the instance id.
    assert event_type == "my_event.inst-1"
    assert obj == payload

    # User headers are preserved and the session id is passed explicitly.
    assert call.kwargs["extra_headers"] == {"x-header": "value"}
    assert call.kwargs["session_id"] == "sess-42"


@pytest.mark.asyncio
async def test_event_session_publish_without_extra_headers():
    messenger = AsyncMock()
    session = EventSession(
        messenger, service_name="ServiceA", instance_id=123, session_id=999
    )

    await session.publish("evt", {"foo": "bar"})

    messenger.publish.assert_awaited_once()
    call = messenger.publish.call_args

    # instance_id and session_id are cast to str
    assert call.args[0] == "evt.123"
    assert call.kwargs["session_id"] == "999"


@pytest.mark.asyncio
async def test_event_session_publish_forwards_flow_id():
    messenger = AsyncMock()
    session = EventSession(
        messenger, service_name="ServiceA", instance_id="inst-1", session_id="sess-42"
    )

    await session.publish("my_event", {"foo": "bar"}, flow_id="custom-flow")

    messenger.publish.assert_awaited_once()
    assert messenger.publish.call_args.kwargs["flow_id"] == "custom-flow"


@pytest.mark.asyncio
async def test_event_session_publish_rejects_reserved_header():
    messenger = AsyncMock()
    session = EventSession(
        messenger, service_name="ServiceA", instance_id="inst-1", session_id="sess-42"
    )

    with pytest.raises(ValueError):
        await session.publish(
            "my_event", {"foo": "bar"}, extra_headers={"service_name": "spoofed"}
        )

    messenger.publish.assert_not_awaited()
