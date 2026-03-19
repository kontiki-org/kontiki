import logging

KONTIKI = "kontiki"

log = logging.getLogger(KONTIKI)


def setup_logger():
    if not log.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        log.addHandler(handler)
        log.setLevel(logging.INFO)


def get_kontiki_prefix():
    return f"{KONTIKI}_"


def get_kontiki_header_name(name):
    return f"{get_kontiki_prefix()}{name}"
