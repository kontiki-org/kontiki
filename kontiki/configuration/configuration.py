DEFAULT_LOGGING_CONFIGURATION = {
    "version": 1,
    "disable_existing_loggers": True,
    "formatters": {
        "default": {
            "format": (
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s -"
                " %(filename)s:%(lineno)d"
            )
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "level": "DEBUG",
        }
    },
    "root": {
        "handlers": ["console"],
        "level": "DEBUG",
    },
}
