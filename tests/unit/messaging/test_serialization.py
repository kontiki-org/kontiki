from kontiki.messaging.serialization import Serializer


def test_json_serializer_uses_json_format():
    """V2.0 uses JSON-only serialization."""
    config = {}
    serializer = Serializer(config)

    # Test serialization
    test_data = {"key": "value", "number": 42}
    serialized = serializer.dumps(test_data)
    assert b'"key"' in serialized  # JSON should contain the key
    assert b'"value"' in serialized

    # Test deserialization
    deserialized = serializer.loads(serialized)
    assert deserialized == test_data
