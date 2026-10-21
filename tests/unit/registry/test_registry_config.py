import pytest
from pydantic import ValidationError

from kontiki.container import ServiceContainer
from kontiki.registry.server.delegates.activity_tracking import ActivityTracker
from kontiki.registry.server.service import RegistryConfig, ServiceRegistry


class _Core:
    def __init__(self, settings):
        class Container:
            pass

        self.container = Container()
        self.container.settings = settings


def test_registry_config_defaults_when_activity_tracker_is_absent():
    config = RegistryConfig.model_validate({})
    assert config.activity_tracker.ttl_minutes == 0
    assert config.activity_tracker.ttl_hours == 24 * 7
    assert config.activity_tracker.disable is False
    assert config.activity_tracker.cleanup_interval_seconds == 3600


def test_registry_config_rejects_unknown_activity_tracker_key():
    with pytest.raises(ValidationError):
        RegistryConfig.model_validate({"activity_tracker": {"ttl": 1}})


@pytest.mark.asyncio
async def test_registry_setup_rejects_invalid_activity_tracker():
    container = ServiceContainer(
        ServiceRegistry,
        version="test",
        config_paths=None,
        disable_service_registration=True,
        config={"activity_tracker": {"ttl_hours": "168"}},
    )
    with pytest.raises(ValidationError):
        await container.setup()
    assert container.settings is None


@pytest.mark.asyncio
async def test_activity_tracker_reads_validated_settings():
    settings = RegistryConfig.model_validate(
        {"activity_tracker": {"ttl_minutes": 5, "disable": True}}
    )
    tracker = ActivityTracker(_Core(settings))
    await tracker.setup()
    assert tracker.ttl_minutes == 5
    assert tracker.ttl == 5
    assert tracker.disable_tracking is True
    assert tracker.cleanup_interval == 3600
    assert tracker.ttl_hours == 24 * 7
