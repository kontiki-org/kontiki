from kontiki.utils import KONTIKI, log

# -----------------------------------------------------------------------------

_MISSING = object()


class ConfigParameterError(Exception):
    pass


class ConfigParameter:
    def __init__(self, path_or_key):
        self.path_or_key = path_or_key

    def get(self, config, default=_MISSING):
        keys = self.path_or_key.split(".")
        try:
            value = config
            for key in keys:
                value = value[key]
            return value
        except KeyError as err:
            if default is not _MISSING:
                msg = "No parameter %s defined in configuration. Use default value %s"
                log.info(msg, self.path_or_key, default)
                return default
            raise ConfigParameterError(
                f"Configuration paramater path {self.path_or_key} not found."
            ) from err


def resolve_parameter_path(config, path_or_key, use_config):
    if use_config:
        return ConfigParameter(path_or_key).get(config)
    return path_or_key


def get_kontiki_parameter(config, path, default=_MISSING):
    return get_parameter(config, f"{KONTIKI}.{path}", default)


def get_parameter(config, path, default=_MISSING):
    try:
        if config:
            return ConfigParameter(path).get(config, default)
        if default is not None:
            msg = "No parameter %s defined in configuration. Use default value %s"
            log.info(msg, path, default)

            return default
        msg = "No configuration found. No default value provided."
        log.error(msg)
        raise ConfigParameterError(msg)
    except Exception as e:
        log.error(str(e))
        raise e
