from kontiki.messaging.common import (
    AMQP_DEFAULT_URL,
    create_tls_context,
    get_amqp_url,
    get_rpc_timeout,
)


def test_get_amqp_url_with_config():
    config = {"kontiki": {"amqp": {"url": "amqp://user:pass@host:5672/"}}}
    assert get_amqp_url(config) == "amqp://user:pass@host:5672/"


def test_get_amqp_url_without_config_uses_default():
    config = {}
    assert get_amqp_url(config) == AMQP_DEFAULT_URL


def test_get_rpc_timeout_with_config():
    config = {"kontiki": {"amqp": {"rpc": {"timeout": 42}}}}
    assert get_rpc_timeout(config) == 42


def test_get_rpc_timeout_without_config_uses_default():
    config = {}
    assert get_rpc_timeout(config) == 10


def test_create_tls_context_disabled_when_not_dict():
    # Non-dict configuration should result in no TLS context
    config = {"kontiki": {"amqp": {"tls": "not-a-dict"}}}
    assert create_tls_context(config) is None


def test_create_tls_context_disabled_when_flag_false():
    config = {"kontiki": {"amqp": {"tls": {"enabled": False}}}}
    assert create_tls_context(config) is None


def test_create_tls_context_minimal(monkeypatch):
    # Configure TLS with enabled flag and a CA path, but don't rely on
    # the real ssl implementation. We only care that a non-None context
    # is returned when configuration is valid.
    config = {
        "kontiki": {
            "amqp": {
                "tls": {
                    "enabled": True,
                    "ca_cert": "/path/to/ca.pem",
                }
            }
        }
    }

    fake_ctx = object()

    def fake_create_default_context(*args, **kwargs):
        # Ensure the function is called with the provided cafile
        assert "cafile" in kwargs or args
        return fake_ctx

    monkeypatch.setattr(
        "kontiki.messaging.common.ssl.create_default_context",
        fake_create_default_context,
    )

    ctx = create_tls_context(config)
    assert ctx is fake_ctx
