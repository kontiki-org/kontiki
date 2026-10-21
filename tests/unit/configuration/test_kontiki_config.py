import pytest
from pydantic import ValidationError

from kontiki.configuration.model import KontikiConfig
from kontiki.container import ServiceContainer
from kontiki.messaging.common import AMQP_DEFAULT_URL


def test_missing_kontiki_block_uses_defaults_without_writing_them():
    config = {}
    parsed = KontikiConfig.model_validate(config.get("kontiki", {}))
    assert parsed.amqp.url == AMQP_DEFAULT_URL
    assert parsed.amqp.required is True
    assert parsed.amqp.disable is False
    assert parsed.heartbeat.interval == 60
    assert parsed.shutdown.grace_seconds == 25
    assert config == {}


def test_unknown_kontiki_key_is_rejected():
    with pytest.raises(ValidationError):
        KontikiConfig.model_validate({"heartbat": {"interval": 5}})


def test_wrong_type_is_rejected():
    with pytest.raises(ValidationError):
        KontikiConfig.model_validate({"heartbeat": {"interval": "60"}})


def test_grace_seconds_accepts_a_fraction():
    parsed = KontikiConfig.model_validate({"shutdown": {"grace_seconds": 0.05}})
    assert parsed.shutdown.grace_seconds == 0.05


def test_max_attempts_must_be_at_least_one():
    with pytest.raises(ValidationError):
        KontikiConfig.model_validate({"amqp": {"max_attempts": 0}})


def test_empty_service_name_is_rejected():
    with pytest.raises(ValidationError):
        KontikiConfig.model_validate({"service_name": ""})


def test_empty_peer_target_is_rejected():
    with pytest.raises(ValidationError):
        KontikiConfig.model_validate({"peers": {"billing": ""}})


def test_tls_enabled_requires_ca_cert():
    with pytest.raises(ValidationError):
        KontikiConfig.model_validate({"amqp": {"tls": {"enabled": True}}})


def test_amqp_disable_alone_is_valid():
    parsed = KontikiConfig.model_validate({"amqp": {"disable": True}})
    assert parsed.amqp.disable is True
    assert parsed.amqp.required is True
    assert "required" not in parsed.amqp.model_fields_set


def test_amqp_disable_rejects_explicit_required_true():
    with pytest.raises(ValidationError):
        KontikiConfig.model_validate({"amqp": {"disable": True, "required": True}})


def test_amqp_disable_rejects_explicit_registration_enabled():
    with pytest.raises(ValidationError):
        KontikiConfig.model_validate(
            {
                "amqp": {"disable": True},
                "registration": {"disable": False},
            }
        )


@pytest.mark.asyncio
async def test_setup_validates_kontiki_before_delegates():
    class BareService:
        pass

    container = ServiceContainer(
        BareService,
        version="test",
        config_paths=None,
        disable_service_registration=True,
        config={"kontiki": {"http": {"port": "8080"}}},
    )
    with pytest.raises(ValidationError):
        await container.setup()
    assert container.kontiki is None


@pytest.mark.asyncio
async def test_setup_keeps_amqp_disable_without_required():
    class BareService:
        pass

    container = ServiceContainer(
        BareService,
        version="test",
        config_paths=None,
        disable_service_registration=False,
        config={"kontiki": {"amqp": {"disable": True}}},
    )
    await container.setup()
    assert container.kontiki.amqp.disable is True
    assert "required" not in container.config["kontiki"]["amqp"]
    await container.stop()
