import copy
import logging

from kontiki.runtime.handler_scope import (
    FLOW_ID_LENGTH,
    FLOW_ID_UNSET,
    current_flow_id,
    flow_id_header_name,
    format_flow_id_for_log,
    generate_flow_id,
    reset_handler_context,
    set_flow_id,
    set_handler_context,
)

# Re-export for existing callers / tests.
__all__ = [
    "FLOW_ID_LENGTH",
    "FLOW_ID_UNSET",
    "FlowIdFilter",
    "apply_outbound_flow_id",
    "current_flow_id",
    "enter_flow_context",
    "enter_flow_from_headers",
    "flow_id_header_name",
    "format_flow_id_for_log",
    "generate_flow_id",
    "prepare_logging_config",
    "reset_flow_id",
    "resolve_flow_id",
]


def enter_flow_context(flow_id=None):
    return set_handler_context(kind=None, operation=None, flow_id=flow_id)


def reset_flow_id(token):
    reset_handler_context(token)


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

    return set_flow_id(value)


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
