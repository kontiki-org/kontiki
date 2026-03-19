from kontiki.utils import log


def extract_schema(model_class):
    try:
        # Pydantic v2
        if hasattr(model_class, "model_json_schema"):
            return model_class.model_json_schema()  # type: ignore[attr-defined]
        # Pydantic v1
        if hasattr(model_class, "schema"):
            return model_class.schema()  # type: ignore[attr-defined]
        # Fallback
        return {"type": "object", "description": "Custom model"}
    except Exception as exc:  # pragma: no cover - defensive
        log.warning("Could not extract schema from %s: %s", model_class, exc)
        return {"type": "object", "description": "Model schema extraction failed"}


def parse_with_model(model_class, data):
    """Parse/validate data using a Pydantic model (v1 or v2)."""
    if hasattr(model_class, "model_validate"):
        return model_class.model_validate(data)  # type: ignore[attr-defined]
    if hasattr(model_class, "parse_obj"):
        return model_class.parse_obj(data)  # type: ignore[attr-defined]
    # If unknown type, just return data
    return data
