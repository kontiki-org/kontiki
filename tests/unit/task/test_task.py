from datetime import datetime
from unittest.mock import patch

import pytest

from kontiki.configuration.parameter import ConfigParameterError
from kontiki.task.task import (
    Task,
    resolve_task_cron,
    seconds_until_next_cron,
    task,
    validate_cron_expression,
)


def test_interval_and_cron_are_mutually_exclusive():
    with pytest.raises(ValueError, match="mutually exclusive"):
        task(interval=10, cron="0 2 * * *")


def test_interval_or_cron_is_required():
    with pytest.raises(ValueError, match="pass interval or cron"):
        task()


def test_use_config_only_applies_to_cron():
    with pytest.raises(ValueError, match="use_config"):
        task(interval=10, use_config=True)


def test_interval_immediate_defaults_true():
    @task(interval=10)
    async def tick():
        pass

    assert tick._task_interval == 10
    assert tick._task_immediate is True
    assert not hasattr(tick, "_task_cron")


def test_positional_interval_unchanged():
    @task(10, immediate=False)
    async def tick():
        pass

    assert tick._task_interval == 10
    assert tick._task_immediate is False


def test_cron_immediate_defaults_false():
    @task(cron="0 2 * * *")
    async def backup():
        pass

    assert backup._task_cron == "0 2 * * *"
    assert backup._task_immediate is False
    assert backup._task_use_config is False
    assert not hasattr(backup, "_task_interval")


def test_cron_immediate_true_is_allowed():
    @task(cron="0 2 * * *", immediate=True)
    async def backup():
        pass

    assert backup._task_immediate is True


def test_invalid_cron_fails_at_decoration():
    with pytest.raises(ValueError, match="Invalid crontab"):
        task(cron="0 2 * * 8")


def test_six_field_cron_is_rejected():
    with pytest.raises(ValueError, match="5-field"):
        task(cron="0 0 2 * * *")


def test_use_config_does_not_validate_expression_at_decoration():
    @task(cron="app.backup.schedule", use_config=True)
    async def backup():
        pass

    assert backup._task_cron == "app.backup.schedule"
    assert backup._task_use_config is True


def test_resolve_cron_literal():
    assert resolve_task_cron({}, "0 2 * * *", False) == "0 2 * * *"


def test_resolve_cron_from_config():
    config = {"app": {"backup": {"schedule": "30 4 * * 1"}}}
    assert resolve_task_cron(config, "app.backup.schedule", True) == "30 4 * * 1"


def test_resolve_cron_missing_key_fails_fast():
    with pytest.raises(ConfigParameterError):
        resolve_task_cron({"app": {}}, "app.backup.schedule", True)


def test_resolve_cron_invalid_config_value_fails_fast():
    config = {"app": {"backup": {"schedule": "0 2 * * 8"}}}
    with pytest.raises(ValueError, match="Invalid crontab"):
        resolve_task_cron(config, "app.backup.schedule", True)


def test_resolve_cron_rejects_non_string_config_value():
    config = {"app": {"backup": {"schedule": 120}}}
    with pytest.raises(ValueError, match="5-field"):
        resolve_task_cron(config, "app.backup.schedule", True)


def test_seconds_until_next_cron_before_occurrence():
    now = datetime(2026, 9, 9, 1, 59, 0)
    delay = seconds_until_next_cron("0 2 * * *", now)
    assert delay == 60


def test_seconds_until_next_cron_after_occurrence_skips_to_next_day():
    now = datetime(2026, 9, 9, 2, 0, 1)
    delay = seconds_until_next_cron("0 2 * * *", now)
    expected = (datetime(2026, 9, 10, 2, 0, 0) - now).total_seconds()
    assert delay == expected


def test_validate_cron_expression_accepts_standard_fields():
    validate_cron_expression("*/5 0 * * 1-5")


@pytest.mark.asyncio
async def test_cron_loop_executes_after_sleep_then_waits_from_now():
    runs = []

    async def user_task():
        runs.append("tick")

    scheduled = Task(None, user_task, immediate=False, cron="0 2 * * *")
    sleeps = []
    n = 0

    async def fake_sleep(delay):
        nonlocal n
        sleeps.append(delay)
        n += 1
        if n >= 2:
            scheduled.running = False

    with patch("kontiki.task.task.asyncio.sleep", fake_sleep):
        with patch(
            "kontiki.task.task.seconds_until_next_cron",
            side_effect=[10, 86400],
        ):
            scheduled.running = True
            await scheduled._run()

    assert runs == ["tick"]
    assert sleeps == [10, 86400]
