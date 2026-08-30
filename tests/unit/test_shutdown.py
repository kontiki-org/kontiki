import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from kontiki.container import ServiceContainer
from kontiki.delegate import ServiceDelegate


class _StubService:
    pass


class _StubDelegate(ServiceDelegate):
    pass


def _make_container(config=None):
    if config is None:
        config = {"kontiki": {"shutdown": {"grace_seconds": 0.05}}}
    return ServiceContainer(
        _StubService,
        version="test",
        config_paths=None,
        disable_service_registration=True,
        config=config,
    )


def _attach_shutdown_stubs(container):
    calls = []

    container.http_server = AsyncMock()
    container.http_server.stop_accepting = AsyncMock(
        side_effect=lambda: calls.append("http.stop_accepting")
    )
    container.http_server.drain = AsyncMock(
        side_effect=lambda: calls.append("http.drain")
    )

    container.amqp_consumer = AsyncMock()
    container.amqp_consumer.connection = object()
    container.amqp_consumer.work_in_flight = MagicMock()
    container.amqp_consumer.work_in_flight.count = 0
    container.amqp_consumer.stop_accepting = AsyncMock(
        side_effect=lambda: calls.append("amqp.stop_accepting")
    )
    container.amqp_consumer.drain = AsyncMock(
        side_effect=lambda: calls.append("amqp.drain")
    )
    container.amqp_consumer.force_close = AsyncMock(
        side_effect=lambda: calls.append("amqp.force_close")
    )

    heartbeat = AsyncMock()
    heartbeat.stop = AsyncMock(side_effect=lambda: calls.append("heartbeat.stop"))
    messenger = AsyncMock()
    messenger.stop = AsyncMock(side_effect=lambda: calls.append("messenger.stop"))

    container.delegates = {
        "_kontiki_heartbeat": heartbeat,
        "messenger": messenger,
    }

    task = AsyncMock()
    task.stop_accepting = MagicMock(
        side_effect=lambda: calls.append("task.stop_accepting")
    )
    task.drain = AsyncMock(side_effect=lambda: calls.append("task.drain"))
    task.force_stop = AsyncMock(side_effect=lambda: calls.append("task.force_stop"))
    container.tasks = [task]

    registry = AsyncMock()
    registry.stop_accepting = AsyncMock(
        side_effect=lambda: calls.append("registry.stop_accepting")
    )
    registry.unregister = AsyncMock(
        side_effect=lambda: calls.append("registry.unregister")
    )
    registry.stop = AsyncMock(side_effect=lambda: calls.append("registry.stop"))
    container.service_registry_client = registry

    return calls


@pytest.mark.asyncio
async def test_stop_runs_phases_in_order():
    container = _make_container()
    calls = _attach_shutdown_stubs(container)

    await container.stop()

    assert calls.index("http.stop_accepting") < calls.index("http.drain")
    assert calls.index("amqp.stop_accepting") < calls.index("amqp.drain")
    assert calls.index("amqp.drain") < calls.index("amqp.force_close")
    assert calls.index("task.stop_accepting") < calls.index("task.drain")
    assert calls.index("task.drain") < calls.index("task.force_stop")
    assert calls.index("heartbeat.stop") < calls.index("messenger.stop")
    assert container.shutting_down is True


@pytest.mark.asyncio
async def test_stop_heartbeat_before_business_delegates():
    container = _make_container()
    calls = _attach_shutdown_stubs(container)

    await container.stop()

    assert calls.index("heartbeat.stop") < calls.index("messenger.stop")


@pytest.mark.asyncio
async def test_stop_unregisters_in_phase1():
    container = _make_container()
    calls = _attach_shutdown_stubs(container)

    await container.stop()

    phase1_end = calls.index("amqp.drain")
    assert calls.index("registry.unregister") < phase1_end
    assert calls.index("registry.stop_accepting") < phase1_end


@pytest.mark.asyncio
async def test_stop_timeout_forces_phase3():
    container = _make_container({"kontiki": {"shutdown": {"grace_seconds": 0.01}}})
    calls = _attach_shutdown_stubs(container)

    async def slow_drain():
        calls.append("amqp.drain")
        await asyncio.sleep(1)

    container.amqp_consumer.drain = slow_drain

    await container.stop()

    assert "amqp.force_close" in calls


@pytest.mark.asyncio
async def test_stop_is_idempotent():
    container = _make_container()
    _attach_shutdown_stubs(container)

    await container.stop()
    await container.stop()

    container.http_server.stop_accepting.assert_awaited_once()


@pytest.mark.asyncio
async def test_stop_waits_for_amqp_in_flight_when_drain_completes():
    from kontiki.messaging.consumer.core import WorkInFlight

    container = _make_container()
    calls = _attach_shutdown_stubs(container)

    work = WorkInFlight()
    container.amqp_consumer.work_in_flight = work

    async def real_drain():
        calls.append("amqp.drain")
        await work.wait_empty()

    container.amqp_consumer.drain = real_drain

    async def release_in_flight():
        await asyncio.sleep(0.02)
        work.end()

    work.begin()
    asyncio.create_task(release_in_flight())

    await container.stop()

    assert "amqp.force_close" in calls
