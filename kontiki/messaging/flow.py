import copy
import importlib
import logging
import re
from pathlib import Path

from kontiki.configuration.configuration import DEFAULT_LOG_FORMAT
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
    "ServiceIdentityFilter",
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
    "sanitize_service_name_for_log",
    "short_instance_id",
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


class ServiceIdentityFilter(logging.Filter):
    def __init__(self, name="", service_name="", short_instance_id=""):
        super().__init__(name)
        self.service_name = service_name
        self.short_instance_id = short_instance_id

    def filter(self, record):
        record.service_name = self.service_name
        record.short_instance_id = self.short_instance_id
        return True


def sanitize_service_name_for_log(service_name):
    return re.sub(r"[^A-Za-z0-9._-]", "_", service_name)


def short_instance_id(instance_id):
    return instance_id.replace("-", "")[:12]


def _resolve_class(class_path):
    if not isinstance(class_path, str):
        return class_path
    module_name, _, qual = class_path.rpartition(".")
    if not module_name:
        raise ValueError(f"Invalid logging handler class: {class_path!r}")
    module = importlib.import_module(module_name)
    return getattr(module, qual)


def _is_file_handler(handler_conf):
    class_path = handler_conf.get("class")
    if class_path is None:
        return False
    return issubclass(_resolve_class(class_path), logging.FileHandler)


def _impose_log_filenames(config, directory, safe_name, short_id):
    path = str(Path(directory) / f"{safe_name}-{short_id}.log")
    file_handlers = []
    for handler_conf in config.get("handlers", {}).values():
        if _is_file_handler(handler_conf):
            file_handlers.append(handler_conf)
    if not file_handlers:
        return
    Path(directory).mkdir(parents=True, exist_ok=True)
    for handler_conf in file_handlers:
        if "filename" in handler_conf:
            logging.getLogger("kontiki").warning(
                "Ignoring logging handler filename %r; using Kontiki path %s",
                handler_conf["filename"],
                path,
            )
        handler_conf["filename"] = path


def _inject_defaults(config):
    if "version" not in config:
        config["version"] = 1
    if "disable_existing_loggers" not in config:
        config["disable_existing_loggers"] = True
    if "formatters" not in config:
        config["formatters"] = {
            "default": {"format": DEFAULT_LOG_FORMAT},
        }
        for handler_conf in config.get("handlers", {}).values():
            if "formatter" not in handler_conf:
                handler_conf["formatter"] = "default"
    # Keep framework logs visible when disable_existing_loggers is true.
    loggers = config.setdefault("loggers", {})
    if "kontiki" not in loggers:
        loggers["kontiki"] = {
            "level": "INFO",
            "propagate": True,
        }


def prepare_logging_config(logging_config, service_name=None, instance_id=None):
    # Strip Kontiki extensions, impose file paths, inject filters / defaults.
    config = copy.deepcopy(logging_config)
    directory = config.pop("directory", None)
    if directory is not None and not isinstance(directory, str):
        raise ValueError(
            "logging.directory must be a string, " f"got {type(directory).__name__}"
        )
    if directory is not None and not directory:
        raise ValueError("logging.directory must be a non-empty string")

    safe_name = sanitize_service_name_for_log(service_name or "")
    short_id = short_instance_id(instance_id or "")

    if directory is not None:
        _impose_log_filenames(config, directory, safe_name, short_id)

    _inject_defaults(config)

    filters = config.setdefault("filters", {})
    filters["kontiki_flow_id"] = {
        "()": "kontiki.messaging.flow.FlowIdFilter",
    }
    filters["kontiki_service_identity"] = {
        "()": "kontiki.messaging.flow.ServiceIdentityFilter",
        "service_name": safe_name,
        "short_instance_id": short_id,
    }
    for handler_conf in config.get("handlers", {}).values():
        flist = handler_conf.setdefault("filters", [])
        if "kontiki_flow_id" not in flist:
            flist.append("kontiki_flow_id")
        if "kontiki_service_identity" not in flist:
            flist.append("kontiki_service_identity")
    return config
