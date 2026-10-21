import pytest
from pydantic import BaseModel, ConfigDict, ValidationError

from kontiki.container import ServiceContainer
from kontiki.delegate import ServiceDelegate

# -----------------------------------------------------------------------------


class AppConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    token: str
    poll_interval: int = 30


class PublicFacts(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    environment: str


class ServiceConfig(BaseModel):
    app: AppConfig
    public: PublicFacts | None = None


class RecordingDelegate(ServiceDelegate):
    def __init__(self):
        super().__init__()
        self.seen = None
        self.called = False

    async def setup(self):
        self.called = True
        self.seen = self.container.settings.app.token


def _container(service_cls, config):
    return ServiceContainer(
        service_cls,
        version="test",
        config_paths=None,
        disable_service_registration=True,
        config=config,
    )


def _disabled_amqp(config):
    config["kontiki"] = {"amqp": {"disable": True}}
    return config


@pytest.mark.asyncio
async def test_setup_without_config_model_leaves_settings_unset():
    class BareService:
        pass

    config = _disabled_amqp({})
    container = _container(BareService, config)
    await container.setup()
    assert container.settings is None
    await container.stop()


@pytest.mark.asyncio
async def test_setup_validates_declared_keys_only():
    class ConfiguredService:
        config_model = ServiceConfig
        delegate = RecordingDelegate()

    config = _disabled_amqp(
        {
            "app": {"token": "s3cret"},
            "publc": {"environment": "earth"},
        }
    )
    container = _container(ConfiguredService, config)
    await container.setup()

    assert container.settings.app.token == "s3cret"
    assert container.settings.app.poll_interval == 30
    assert container.settings.public is None
    assert container.config["app"] == {"token": "s3cret"}
    assert container.config["publc"] == {"environment": "earth"}
    assert ConfiguredService.delegate.called is True
    assert ConfiguredService.delegate.seen == "s3cret"
    await container.stop()


@pytest.mark.asyncio
async def test_setup_uses_inherited_config_model():
    class BaseService:
        config_model = ServiceConfig

    class ChildService(BaseService):
        pass

    config = _disabled_amqp({"app": {"token": "s3cret", "poll_interval": 10}})
    container = _container(ChildService, config)
    await container.setup()
    assert container.settings.app.poll_interval == 10
    await container.stop()


@pytest.mark.asyncio
async def test_setup_rejects_invalid_config_before_delegates():
    class ConfiguredService:
        config_model = ServiceConfig
        delegate = RecordingDelegate()

    container = _container(ConfiguredService, {"app": {}})
    with pytest.raises(ValidationError):
        await container.setup()
    assert container.settings is None
    assert ConfiguredService.delegate.called is False


@pytest.mark.asyncio
async def test_setup_rejects_unknown_key_inside_declared_model():
    class ConfiguredService:
        config_model = ServiceConfig

    container = _container(
        ConfiguredService,
        {"app": {"token": "s3cret", "extra": True}},
    )
    with pytest.raises(ValidationError):
        await container.setup()
    assert container.settings is None
