import kontiki.messaging.serialization as serialization_module
from kontiki.messaging.serialization import Serializer


def test_json_serialization_logs_deprecation_warning_once(monkeypatch):
    warnings = []
    monkeypatch.setattr(
        serialization_module,
        "_json_deprecation_warned",
        False,
    )
    monkeypatch.setattr(
        serialization_module.log,
        "warning",
        lambda msg, *args: warnings.append(msg % args if args else msg),
    )

    config = {"kontiki": {"amqp": {"serialization": "json"}}}
    Serializer(config)
    Serializer(config)

    assert len(warnings) == 1
    assert "deprecated" in warnings[0]
    assert "pickle" in warnings[0]


def test_pickle_serialization_does_not_warn(monkeypatch):
    warnings = []
    monkeypatch.setattr(
        serialization_module,
        "_json_deprecation_warned",
        False,
    )
    monkeypatch.setattr(
        serialization_module.log,
        "warning",
        lambda msg, *args: warnings.append(msg),
    )

    Serializer({})

    assert warnings == []
