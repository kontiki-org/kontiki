import secrets
from contextvars import ContextVar
from dataclasses import dataclass

from kontiki.utils import get_kontiki_header_name

FLOW_ID_LENGTH = 12
FLOW_ID_UNSET = "[no flow]"


@dataclass
class HandlerContext:
    kind: str | None
    operation: str | None
    flow_id: str | None


@dataclass
class ScopeToken:
    context_token: object
    work_in_flight: object = None


_handler_context_var = ContextVar("kontiki_handler_context", default=None)


def flow_id_header_name():
    return get_kontiki_header_name("flow_id")


def generate_flow_id():
    return secrets.token_hex(6)


def format_flow_id_for_log(flow_id=None):
    if flow_id is None:
        return FLOW_ID_UNSET
    return f"[flow={flow_id}]"


def _get_raw_context():
    return _handler_context_var.get()


def current_handler_context():
    ctx = _get_raw_context()
    if ctx is None or ctx.kind is None:
        return None
    return ctx


def current_flow_id():
    ctx = _get_raw_context()
    if ctx is None:
        return None
    return ctx.flow_id


def set_handler_context(kind, operation, flow_id):
    return _handler_context_var.set(
        HandlerContext(kind=kind, operation=operation, flow_id=flow_id)
    )


def reset_handler_context(token):
    _handler_context_var.reset(token)


def set_flow_id(value):
    ctx = _get_raw_context()
    if ctx is None:
        _handler_context_var.set(
            HandlerContext(kind=None, operation=None, flow_id=value)
        )
    else:
        ctx.flow_id = value
    return value


def enter_handler_scope(kind, operation, *, headers=None, work_in_flight=None):
    if kind in ("http", "task"):
        flow_id = generate_flow_id()
    elif headers:
        flow_id = headers.get(flow_id_header_name())
    else:
        flow_id = None

    context_token = set_handler_context(kind, operation, flow_id)
    if work_in_flight is not None:
        work_in_flight.begin()
    return ScopeToken(context_token=context_token, work_in_flight=work_in_flight)


def reset_handler_scope(scope_token):
    if scope_token.work_in_flight is not None:
        scope_token.work_in_flight.end()
    reset_handler_context(scope_token.context_token)


def registry_exception_context():
    ctx = current_handler_context()
    if ctx is None:
        return {}
    if ctx.kind == "http":
        method, _, path = ctx.operation.partition(" ")
        return {"entrypoint": "http", "method": method, "path": path}
    return {"entrypoint": ctx.kind, "name": ctx.operation}
