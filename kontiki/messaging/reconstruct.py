import types
from typing import Union, get_args, get_origin


def model_type(hint):
    """Concrete class to build from a payload dict.

    `Model` and `Model | None` resolve to `Model`. Other unions and generic
    aliases (list[str], …) do not.
    """
    origin = get_origin(hint)
    if origin is None:
        if isinstance(hint, type):
            return hint
        return None
    if origin is Union or origin is types.UnionType:
        args = [arg for arg in get_args(hint) if arg is not type(None)]
        if len(args) == 1:
            return model_type(args[0])
    return None


def reconstruct(hint, data):
    if not isinstance(data, dict):
        return data
    model = model_type(hint)
    if model is None:
        return data
    return model(**data)
