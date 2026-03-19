from unittest.mock import AsyncMock

import pytest

from kontiki.messaging.publisher.session import EventSession
from kontiki.utils import get_kontiki_header_name


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
    headers = call.kwargs["extra_headers"]

    # Routing key must be suffixed with the instance id.
    assert event_type == "my_event.inst-1"
    assert obj == payload

    # Headers must contain the kontiki_session_id and preserve extra headers.
    session_key = get_kontiki_header_name("session_id")
    assert headers[session_key] == "sess-42"
    assert headers["x-header"] == "value"


@pytest.mark.asyncio
async def test_event_session_publish_without_extra_headers():
    messenger = AsyncMock()
    session = EventSession(
        messenger, service_name="ServiceA", instance_id=123, session_id=999
    )

    await session.publish("evt", {"foo": "bar"})

    messenger.publish.assert_awaited_once()
    call = messenger.publish.call_args
    event_type, obj = call.args
    headers = call.kwargs["extra_headers"]

    # instance_id and session_id are cast to str
    assert event_type == "evt.123"
    session_key = get_kontiki_header_name("session_id")
    assert headers[session_key] == "999"
