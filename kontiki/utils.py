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


def get_kontiki_prefix():
    return f"{KONTIKI}_"


def get_kontiki_header_name(name):
    return f"{get_kontiki_prefix()}{name}"
