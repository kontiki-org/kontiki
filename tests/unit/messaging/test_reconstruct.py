from typing import get_type_hints

import pytest

from kontiki.messaging.reconstruct import model_type, reconstruct


class Job:
    def __init__(self, name):
        self.name = name


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

    with pytest.raises(TypeError):
        reconstruct(_hint(on_job, "job"), {"nope": 1})


def test_generic_alias_is_left_as_a_dict():
    def on_items(items: list[str]):
        return items

    hint = _hint(on_items, "items")
    assert model_type(hint) is None
    assert reconstruct(hint, {"name": "a"}) == {"name": "a"}
