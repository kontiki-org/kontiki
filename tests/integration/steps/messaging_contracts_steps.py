import json

from behave import then

from kontiki.messaging.publisher.rpc import RpcError


def _strip_schema_noise(value):
    if isinstance(value, dict):
        cleaned = {}
        for key, item in value.items():
            if key in ("title", "description"):
                continue
            cleaned[key] = _strip_schema_noise(item)
        return cleaned
    if isinstance(value, list):
        return [_strip_schema_noise(item) for item in value]
    return value


def _resolve_refs(schema, defs=None):
    if not isinstance(schema, dict):
        return schema
    if defs is None:
        defs = schema.get("$defs") or schema.get("definitions") or {}
    if "$ref" in schema:
        ref = schema["$ref"]
        prefix = "#/$defs/"
        alt = "#/definitions/"
        if ref.startswith(prefix):
            return _resolve_refs(defs[ref[len(prefix) :]], defs)
        if ref.startswith(alt):
            return _resolve_refs(defs[ref[len(alt) :]], defs)
        raise AssertionError(f"Unsupported schema $ref: {ref}")
    resolved = {}
    for key, item in schema.items():
        if key in ("$defs", "definitions"):
            continue
        if isinstance(item, list):
            resolved[key] = [_resolve_refs(part, defs) for part in item]
        else:
            resolved[key] = _resolve_refs(item, defs)
    return resolved


def _schema_matches(actual, expected):
    actual_norm = _strip_schema_noise(_resolve_refs(actual))
    expected_norm = _strip_schema_noise(_resolve_refs(expected))
    return actual_norm == expected_norm


def _entrypoint_matches(actual, expected):
    if actual.get("type") != expected.get("type"):
        return False
    if actual.get("name") != expected.get("name"):
        return False
    if actual.get("handler") != expected.get("handler"):
        return False
    for key in ("mode", "max_attempts", "description", "default"):
        if key in expected and actual.get(key) != expected.get(key):
            return False
    if "parameters" in expected:
        actual_params = actual.get("parameters")
        expected_params = expected["parameters"]
        if not isinstance(actual_params, list) or len(actual_params) != len(
            expected_params
        ):
            return False
        for actual_param, expected_param in zip(actual_params, expected_params):
            if actual_param.get("name") != expected_param.get("name"):
                return False
            if actual_param.get("required") != expected_param.get("required"):
                return False
            if "default" in expected_param:
                if actual_param.get("default") != expected_param.get("default"):
                    return False
            if "schema" in expected_param:
                if not _schema_matches(
                    actual_param.get("schema"), expected_param["schema"]
                ):
                    return False
    elif "parameters" in actual:
        return False
    if "return" in expected:
        if not _schema_matches(actual.get("return"), expected["return"]):
            return False
    elif "return" in actual:
        return False
    if "payload_schema" in expected:
        if not _schema_matches(actual.get("payload_schema"), expected["payload_schema"]):
            return False
    elif "payload_schema" in actual:
        return False
    return True


def _find_entrypoint(services, service_name, entrypoint_type, entrypoint_name):
    service = services.get(service_name)
    if not service:
        raise AssertionError(f"Service {service_name!r} not found in get_services.")
    for instance in service.values():
        for entry in instance.get("metadata", {}).get("entrypoints", []):
            if (
                entry.get("type") == entrypoint_type
                and entry.get("name") == entrypoint_name
            ):
                return entry
    raise AssertionError(
        f"Entrypoint {entrypoint_type} {entrypoint_name!r} not found "
        f"on {service_name}."
    )


@then(
    "the {service_name} entrypoint {entrypoint_type} {entrypoint_name} is"
)
def step_service_entrypoint_contract(
    context, service_name, entrypoint_type, entrypoint_name
):
    expected = json.loads(context.text.strip())
    try:
        services = context.runner.call("ServiceRegistry", "get_services")
    except RpcError as exc:
        raise AssertionError(
            f"get_services failed: {exc.code}: {exc.message}"
        ) from exc
    actual = _find_entrypoint(
        services, service_name, entrypoint_type, entrypoint_name
    )
    assert _entrypoint_matches(actual, expected), (
        f"Entrypoint mismatch for {service_name} "
        f"{entrypoint_type} {entrypoint_name}.\n"
        f"Expected:\n{json.dumps(expected, indent=2)}\n"
        f"Actual:\n{json.dumps(actual, indent=2)}"
    )
