from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

import pytest

from kontiki.registry.events import EXCEPTION_RECORDED
from kontiki.registry.server.delegates.event_tracking import EventTracker


class DummyCore:
    def __init__(self):
        class Container:
            config = {}

        self.container = Container()
        self.channel = None


def _make_message(headers):
    msg = AsyncMock()
    msg.headers = headers

    class _Ctx:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    msg.process = Mock(return_value=_Ctx())
    return msg


@pytest.mark.asyncio
async def test_handle_event_stores_headers_as_is():
    core = DummyCore()
    tracker = EventTracker(core)

    headers = {
        "service_name": "internal-svc",
        "instance_id": "123",
        "event_type": "test_event",
        "custom": "value",
    }

    await tracker._handle_event(_make_message(headers))

    assert len(tracker.events) == 1
    assert tracker.events[0] == headers


@pytest.mark.asyncio
async def test_handle_event_skips_registry_exception_recorded():
    core = DummyCore()
    tracker = EventTracker(core)

    msg = AsyncMock()
    msg.headers = {"event_type": EXCEPTION_RECORDED}

    class _Ctx:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    msg.process = Mock(return_value=_Ctx())

    await tracker._handle_event(msg)

    assert tracker.events == []


def test_purge_expired_events_handles_offset_aware_timestamp():
    # Prevent regression: cleanup must not crash with timezone-aware ISO timestamps.
    core = DummyCore()
    tracker = EventTracker(core)
    tracker.event_ttl = 60

    tracker.events = [
        {"timestamp": datetime.now(timezone.utc).isoformat()},
    ]

    tracker._purge_expired_events()
    assert len(tracker.events) == 1
