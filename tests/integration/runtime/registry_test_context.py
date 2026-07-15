import ast
import re

REGISTER_LINE = re.compile(
    r"Published message to registry\.register: (.+)$"
)
EXCEPTION_LINE = re.compile(
    r"Published message to registry\.exception: (.+)$"
)


def _parse_logged_payload(raw_payload):
    payload = raw_payload
    if " - " in payload:
        payload = payload.rsplit(" - ", 1)[0]
    return ast.literal_eval(payload)


def read_registration_from_log(manager):
    for line in manager.log_file_path.read_text(encoding="utf-8").splitlines():
        match = REGISTER_LINE.search(line)
        if match:
            return _parse_logged_payload(match.group(1))
    raise AssertionError(
        f"registry.register message not found in {manager.log_file_path}"
    )


def read_exception_from_log(manager):
    exception_data = None
    for line in manager.log_file_path.read_text(encoding="utf-8").splitlines():
        match = EXCEPTION_LINE.search(line)
        if match:
            exception_data = _parse_logged_payload(match.group(1))
    if exception_data is None:
        raise AssertionError(
            f"registry.exception message not found in {manager.log_file_path}"
        )
    return exception_data


def placeholders_from_registration(registration):
    return {
        "REGISTRY_TEST_INSTANCE_ID": registration["instance_id"],
        "REGISTRY_TEST_PID": registration["pid"],
        "REGISTRY_TEST_HOST": registration["host"],
    }


def placeholders_from_exception(exception_data):
    return {
        "REGISTRY_TEST_EXCEPTION_TIMESTAMP": exception_data["timestamp"],
    }


def resolve_placeholders(value, placeholders):
    if isinstance(value, dict):
        return {
            resolve_placeholders(key, placeholders): resolve_placeholders(
                item, placeholders
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [resolve_placeholders(item, placeholders) for item in value]
    if isinstance(value, str):
        if value.startswith("[") and value.endswith("]"):
            key = value[1:-1]
            if key in placeholders:
                return placeholders[key]
        return value
    return value


def capture_registry_test_exception_timestamp(context):
    if context.registry_test_manager is None:
        raise AssertionError("Registry test service is not running.")
    exception_data = read_exception_from_log(context.registry_test_manager)
    context.registry_test_placeholders.update(
        placeholders_from_exception(exception_data)
    )
