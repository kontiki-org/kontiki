import pytest

from kontiki.configuration import get_kontiki_parameter, get_parameter
from kontiki.configuration.parameter import ConfigParameterError, resolve_parameter_path

# -----------------------------------------------------------------------------


@pytest.fixture
def config():
    return {"kontiki": {"test": "value"}, "user": {"name": "John Doe"}}


def test_get_kontiki_parameter(config):
    assert get_kontiki_parameter(config, "test") == "value"


def test_get_parameter(config):
    assert get_parameter(config, "user.name") == "John Doe"


def test_get_parameter_with_default(config):
    assert get_parameter(config, "user.surname", default="Smith") == "Smith"


def test_get_parameter_with_default_and_missing_config(config):
    with pytest.raises(ConfigParameterError):
        get_parameter(config, "user.surname")


def test_resolve_parameter_path_direct():
    config = {"path": "/health"}
    assert resolve_parameter_path(config, "/health", use_config=False) == "/health"


def test_resolve_parameter_path_from_config():
    config = {"http": {"health_path": "/health"}}
    assert (
        resolve_parameter_path(config, "http.health_path", use_config=True) == "/health"
    )
