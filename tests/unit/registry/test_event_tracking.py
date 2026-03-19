from unittest.mock import AsyncMock, Mock

import pytest

from kontiki.registry.server.delegates.event_tracking import EventTracker
from kontiki.utils import get_kontiki_prefix


class DummyCore:
    def __init__(self):
        class Container:
            config = {}

        self.container = Container()
        self.channel = None


@pytest.mark.asyncio
async def test_handle_event_normalizes_kontiki_headers_and_preserves_user_headers():
    core = DummyCore()
    tracker = EventTracker(core)

    prefix = get_kontiki_prefix()
    headers = {
        f"{prefix}service_name": "internal-svc",
        f"{prefix}instance_id": "123",
        "event_type": "test_event",
        "custom": "value",
    }

    msg = AsyncMock()
    msg.headers = headers

    class _Ctx:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    # Simule async with message.process():
    msg.process = Mock(return_value=_Ctx())

    await tracker._handle_event(msg)

    assert len(tracker.events) == 1
    normalized = tracker.events[0]

    # Original headers are preserved
    assert normalized[f"{prefix}service_name"] == "internal-svc"
    assert normalized["custom"] == "value"

    # Aliases without prefix are added
    assert normalized["service_name"] == "internal-svc"
    assert normalized["instance_id"] == "123"
    assert normalized["event_type"] == "test_event"


@pytest.mark.asyncio
async def test_handle_event_does_not_override_user_headers():
    core = DummyCore()
    tracker = EventTracker(core)

    prefix = get_kontiki_prefix()
    headers = {
        f"{prefix}service_name": "internal-svc",
        "service_name": "user-svc",
    }

    msg = AsyncMock()
    msg.headers = headers

    class _Ctx:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    msg.process = Mock(return_value=_Ctx())

    await tracker._handle_event(msg)

    assert len(tracker.events) == 1
    normalized = tracker.events[0]

    # Both keys are present, but the user header wins for the bare name.
    assert normalized[f"{prefix}service_name"] == "internal-svc"
    assert normalized["service_name"] == "user-svc"
