DEFAULT_LOG_FORMAT = (
    "%(asctime)s - %(short_instance_id)s - %(levelname)-8s - %(flow_id)-20s - "
    "%(message)s"
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
