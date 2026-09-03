DEFAULT_LOG_FORMAT = (
    "%(asctime)s - %(service_name)s#%(short_instance_id)s - %(levelname)s - "
    "%(flow_id)s - %(message)s"
)

DEFAULT_LOGGING_CONFIGURATION = {
    "version": 1,
    "disable_existing_loggers": True,
    "formatters": {
        "default": {
            "format": DEFAULT_LOG_FORMAT,
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "level": "DEBUG",
        }
    },
    "loggers": {
        "kontiki": {
            "level": "INFO",
            "propagate": True,
        }
    },
    "root": {
        "handlers": ["console"],
        "level": "DEBUG",
    },
}
