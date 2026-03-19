import logging

from kontiki.delegate import ServiceDelegate


class HttpManager(ServiceDelegate):
    def __init__(self):
        self.requests = []
        self.responses = []
        super().__init__()

    def add_response(self, response):
        logging.info("Adding http response %s (%s)", response, self)
        self.responses.append(response)

    def store_request(self, payload):
        logging.info("Storing request %s (%s)", payload, self)
        self.requests.append(payload)

    def get_requests(self):
        if not self.requests:
            logging.warning("No HTTP requests stored.")
        return self.requests

    def get_response(self):
        if self.responses:
            return self.responses.pop(0)
        raise RuntimeError("No more responses to return.")

    def clean(self):
        self.requests.clear()
        self.responses.clear()
