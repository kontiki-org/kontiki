from typing import get_type_hints

import pytest
from pydantic import BaseModel, ValidationError

from kontiki.messaging.reconstruct import hint_json_schema, model_type, reconstruct


class Job(BaseModel):
    name: str


def _hint(fn, name):
    return get_type_hints(fn)[name]


def test_model_or_none_reconstructs_the_model():
    def on_job(job: Job | None):
        return job

    hint = _hint(on_job, "job")
    assert model_type(hint) is Job
    built = reconstruct(hint, {"name": "a"})
    assert isinstance(built, Job)
    assert built.name == "a"


def test_mismatched_model_payload_raises():
    def on_job(job: Job):
        return job

    with pytest.raises(ValidationError):
        reconstruct(_hint(on_job, "job"), {"nope": 1})


def test_scalar_hint_is_validated():
    def on_label(label: str):
        return label

    assert reconstruct(_hint(on_label, "label"), "ok") == "ok"
    with pytest.raises(ValidationError):
        reconstruct(_hint(on_label, "label"), {"not": "a string"})


def test_generic_list_hint_is_validated():
    def on_items(items: list[str]):
        return items

    hint = _hint(on_items, "items")
    assert model_type(hint) is None
    assert reconstruct(hint, ["a", "b"]) == ["a", "b"]
    with pytest.raises(ValidationError):
        reconstruct(hint, {"name": "a"})


def test_hint_json_schema_for_scalar_and_model():
    assert hint_json_schema(str) == {"type": "string"}
    schema = hint_json_schema(Job)
    assert schema["type"] == "object"
    assert "name" in schema["properties"]
