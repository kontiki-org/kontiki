import logging

from kontiki.delegate import ServiceDelegate


class RpcManager(ServiceDelegate):
    def __init__(self):
        self.call_args = []
        self.return_values = []
        super().__init__()

    def add_return_value(self, value):
        logging.info("Adding return value %s", value)
        self.return_values.append(value)

    def store_call_args(self, *args, **kwargs):
        logging.info("Storing args %s and kwargs %s", args, kwargs)
        self.call_args.append((args, kwargs))

    def get_call_args(self):
        if not self.call_args:
            logging.warning("No args stored.")
        return self.call_args

    def get_return_value(self):
        logging.info("Getting return values.")
        try:
            if self.return_values:
                value = self.return_values.pop(0)
                logging.info("Got value %s.", value)
                return value
            raise RuntimeError("No more values to return.")
        except Exception as e:
            logging.error("Error while getting return_value %s", str(e))
            raise e

    def clean(self):
        self.call_args.clear()
        self.return_values.clear()
