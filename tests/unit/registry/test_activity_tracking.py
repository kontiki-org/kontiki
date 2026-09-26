from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

import pytest

from kontiki.messaging.serialization import Serializer
from kontiki.registry.events import CONTEXT_RECORDED, EXCEPTION_RECORDED
from kontiki.registry.server.delegates.activity_tracking import ActivityTracker


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
    tracker = ActivityTracker(core)

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
    tracker = ActivityTracker(core)

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


@pytest.mark.asyncio
async def test_handle_context_appends_to_event_timeline():
    core = DummyCore()
    core.serializer = Serializer({})
    tracker = ActivityTracker(core)

    body = {
        "service_name": "internal-svc",
        "instance_id": "123",
        "context": {"decision": "queued"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "flow_id": "85f847c72921",
        "hop_id": "ae78ac0b9d0c3564",
        "context_id": "a1b2c3d4",
        "entrypoint": "event",
        "operation": "alert.open",
    }

    msg = AsyncMock()
    msg.body = core.serializer.dumps(body)

    class _Ctx:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    msg.process = Mock(return_value=_Ctx())

    await tracker._handle_context(msg)

    assert tracker.events == [{**body, "event_type": CONTEXT_RECORDED}]


def test_purge_expired_events_handles_offset_aware_timestamp():
    # Prevent regression: cleanup must not crash with timezone-aware ISO timestamps.
    core = DummyCore()
    tracker = ActivityTracker(core)
    tracker.ttl = 60

    tracker.events = [
        {"timestamp": datetime.now(timezone.utc).isoformat()},
    ]

    tracker._purge_expired(tracker.events)
    assert len(tracker.events) == 1
