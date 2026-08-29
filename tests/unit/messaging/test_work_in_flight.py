import asyncio

import pytest

from kontiki.messaging.consumer.core import WorkInFlight


@pytest.mark.asyncio
async def test_work_in_flight_begin_end_count():
    work = WorkInFlight()

    work.begin()
    assert work.count == 1

    work.end()
    assert work.count == 0


@pytest.mark.asyncio
async def test_work_in_flight_wait_empty_returns_immediately_when_idle():
    work = WorkInFlight()

    await asyncio.wait_for(work.wait_empty(), timeout=0.1)


@pytest.mark.asyncio
async def test_work_in_flight_wait_empty_blocks_until_end():
    work = WorkInFlight()
    work.begin()

    async def finish_later():
        await asyncio.sleep(0.02)
        work.end()

    asyncio.create_task(finish_later())
    await asyncio.wait_for(work.wait_empty(), timeout=0.5)

    assert work.count == 0
