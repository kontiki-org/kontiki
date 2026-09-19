import secrets
from contextvars import ContextVar
from dataclasses import dataclass

from kontiki.utils import get_kontiki_header_name

FLOW_ID_LENGTH = 12
FLOW_ID_UNSET = "[no flow]"
HOP_ID_LENGTH = 16
EXCEPTION_ID_LENGTH = 16


@dataclass
class HandlerContext:
    kind: str | None
    operation: str | None
    flow_id: str | None
    hop_id: str | None


@dataclass
class ScopeToken:
    context_token: object
    work_in_flight: object = None


_handler_context_var = ContextVar("kontiki_handler_context", default=None)


def flow_id_header_name():
    return get_kontiki_header_name("flow_id")


def hop_id_header_name():
    return get_kontiki_header_name("hop_id")


def parent_hop_id_header_name():
    return get_kontiki_header_name("parent_hop_id")


def entrypoint_header_name():
    return get_kontiki_header_name("entrypoint")


def operation_header_name():
    return get_kontiki_header_name("operation")


def rpc_service_header_name():
    return get_kontiki_header_name("rpc_service")


def generate_flow_id():
    return secrets.token_hex(6)


def generate_hop_id():
    return secrets.token_hex(8)


def generate_exception_id():
    return secrets.token_hex(8)


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


def set_handler_context(kind, operation, flow_id, hop_id=None):
    return _handler_context_var.set(
        HandlerContext(kind=kind, operation=operation, flow_id=flow_id, hop_id=hop_id)
    )


def reset_handler_context(token):
    _handler_context_var.reset(token)


def set_flow_id(value):
    ctx = _get_raw_context()
    if ctx is None:
        _handler_context_var.set(
            HandlerContext(kind=None, operation=None, flow_id=value, hop_id=None)
        )
    else:
        ctx.flow_id = value
    return value


def enter_handler_scope(kind, operation, *, headers=None, work_in_flight=None):
    inbound_flow = None
    inbound_hop = None
    if headers and kind not in ("http", "task"):
        inbound_flow = headers.get(flow_id_header_name())
        inbound_hop = headers.get(hop_id_header_name())
    flow_id = inbound_flow if inbound_flow else generate_flow_id()

    context_token = set_handler_context(kind, operation, flow_id, hop_id=inbound_hop)
    if work_in_flight is not None:
        work_in_flight.begin()
    return ScopeToken(context_token=context_token, work_in_flight=work_in_flight)


def reset_handler_scope(scope_token):
    if scope_token.work_in_flight is not None:
        scope_token.work_in_flight.end()
    reset_handler_context(scope_token.context_token)


def exception_record_fields():
    ctx = current_handler_context()
    if ctx is None:
        return None, None, None, None
    hop_id = ctx.hop_id if ctx.kind not in ("http", "task") else None
    return ctx.flow_id, ctx.kind, ctx.operation, hop_id


def apply_outbound_hop_headers(headers, rpc_service=None):
    hop_key = hop_id_header_name()
    parent_key = parent_hop_id_header_name()
    entry_key = entrypoint_header_name()
    op_key = operation_header_name()
    rpc_key = rpc_service_header_name()

    headers[hop_key] = generate_hop_id()

    ctx = current_handler_context()
    if ctx is None:
        headers.pop(parent_key, None)
        headers.pop(entry_key, None)
        headers.pop(op_key, None)
    else:
        headers[entry_key] = ctx.kind
        headers[op_key] = ctx.operation
        if ctx.kind not in ("http", "task") and ctx.hop_id:
            headers[parent_key] = ctx.hop_id
        else:
            headers.pop(parent_key, None)

    if rpc_service is not None:
        headers[rpc_key] = rpc_service
    else:
        headers.pop(rpc_key, None)
