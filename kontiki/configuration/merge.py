import yaml

from kontiki.utils import log

# -----------------------------------------------------------------------------


class ConfigMergeError(Exception):
    pass


def merge(config_files):
    def _smart_merge(d1, d2):
        shared_keys = d1.keys() & d2.keys()
        only_keys_2 = d2.keys() - d1.keys()
        for key in only_keys_2:
            d1[key] = d2[key]
        errors = []
        warnings = []

        for key in shared_keys:
            if isinstance(d1[key], dict) and isinstance(d2[key], dict):
                suberrors, subwarnings = _smart_merge(d1[key], d2[key])
                subwarnings = [f"{key}:{subkey}" for subkey in subwarnings]
                suberrors = [f"{key}:{subkey}" for subkey in suberrors]

                errors += suberrors
                warnings += subwarnings

            else:
                if d1[key] == d2[key]:
                    warnings.append(key)
                else:
                    errors.append(key)

        return errors, warnings

    config = {}
    for config_file in config_files:
        with open(config_file, "r", encoding="utf-8") as file:
            tmp_dict = yaml.load(file, Loader=yaml.FullLoader)

            if tmp_dict is None:
                tmp_dict = {}
            errors, warnings = _smart_merge(config, tmp_dict)
            if errors:
                for param in errors:
                    log.error("%s definition is inconsistent.", param)
                msg = (
                    "Configuration file merge has failed due to param"
                    " definition inconsistency."
                )
                raise ConfigMergeError(msg)
            if warnings:
                for param in warnings:
                    msg = "%s is defined twice with the same value."
                    log.warning(msg, param)

    return config
