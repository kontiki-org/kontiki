import logging

KONTIKI = "kontiki"

log = logging.getLogger(KONTIKI)


def setup_logger():
    if not log.handlers:
        from kontiki.messaging.flow import FlowIdFilter

        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(flow_id)s - %(message)s"
        )
        handler.setFormatter(formatter)
        handler.addFilter(FlowIdFilter())
        log.addHandler(handler)
        log.setLevel(logging.INFO)


# Header names Kontiki writes on the wire. User extra_headers must not use them.
RESERVED_HEADERS = frozenset(
    {
        "event_type",
        "remote_method",
        "reply_to",
        "session_id",
        "flow_id",
        "hop_id",
        "parent_hop_id",
        "entrypoint",
        "operation",
        "rpc_service",
        "service_name",
        "instance_id",
        "host",
        "timestamp",
    }
)


def validate_extra_headers(extra_headers):
    reserved = sorted(name for name in extra_headers if name in RESERVED_HEADERS)
    if reserved:
        raise ValueError(
            f"Reserved header names are not allowed in extra_headers: "
            f"{', '.join(reserved)}"
        )
