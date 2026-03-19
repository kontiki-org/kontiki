from kontiki.testing.delegates.event_manager import EventManager
from kontiki.testing.delegates.http_manager import HttpManager
from kontiki.testing.delegates.rpc_manager import RpcManager


class MockService:
    event_manager = EventManager()
    remote_call_manager = RpcManager()
    http_manager = HttpManager()

    def get_events(self, wait_for_events=0, timeout=None):
        return self.event_manager.get_events(wait_for_events, timeout)

    def clean_events(self):
        self.event_manager.clean()

    def add_http_response(self, response):
        self.http_manager.add_response(response)

    def get_http_requests(self):
        return self.http_manager.get_requests()

    def clean_http_requests(self):
        self.http_manager.clean()

    def add_remote_return_value(self, value):
        self.remote_call_manager.add_return_value(value)

    def store_call_args(self, *args, **kwargs):
        self.remote_call_manager.store_call_args(args, kwargs)

    def get_return_value(self):
        return self.remote_call_manager.get_return_value()

    def get_remote_calls(self):
        return self.remote_call_manager.get_call_args()

    def clean_remote_calls(self):
        self.remote_call_manager.clean()
