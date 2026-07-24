import copy
import logging
import secrets
from contextvars import ContextVar

from kontiki.utils import get_kontiki_header_name

FLOW_ID_LENGTH = 12
FLOW_ID_UNSET = "[no flow]"


def format_flow_id_for_log(flow_id=None):
    if flow_id is None:
        return FLOW_ID_UNSET
    return f"[flow={flow_id}]"


_flow_id_var = ContextVar("kontiki_flow_id", default=None)


def flow_id_header_name():
    return get_kontiki_header_name("flow_id")


def current_flow_id():
    return _flow_id_var.get()


def generate_flow_id():
    return secrets.token_hex(6)


def enter_flow_context(flow_id=None):
    return _flow_id_var.set(flow_id)


def reset_flow_id(token):
    _flow_id_var.reset(token)


def enter_flow_from_headers(headers):
    flow_id = None
    if headers:
        flow_id = headers.get(flow_id_header_name())
    return enter_flow_context(flow_id)


def resolve_flow_id(flow_id=None, extra_headers=None):
    # Precedence: flow_id= → ContextVar → extra_headers → generate.
    if flow_id is not None:
        value = flow_id
    else:
        value = current_flow_id()
        if value is None and extra_headers:
            value = extra_headers.get(flow_id_header_name())
        if value is None:
            value = generate_flow_id()

    _flow_id_var.set(value)
    return value


def apply_outbound_flow_id(headers, flow_id=None, extra_headers=None):
    value = resolve_flow_id(flow_id=flow_id, extra_headers=extra_headers)
    headers[flow_id_header_name()] = value
    return value


class FlowIdFilter(logging.Filter):
    def filter(self, record):
        record.flow_id = format_flow_id_for_log(current_flow_id())
        return True


def prepare_logging_config(logging_config):
    # Inject the flow_id filter on all handlers. Does not rewrite user formats.
    config = copy.deepcopy(logging_config)
    filters = config.setdefault("filters", {})
    filters["kontiki_flow_id"] = {
        "()": "kontiki.messaging.flow.FlowIdFilter",
    }
    for handler_conf in config.get("handlers", {}).values():
        flist = handler_conf.setdefault("filters", [])
        if "kontiki_flow_id" not in flist:
            flist.append("kontiki_flow_id")
    return config
