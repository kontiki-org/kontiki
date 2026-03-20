from aiohttp import web
from pydantic import BaseModel

from kontiki.delegate import ServiceDelegate
from kontiki.messaging import Messenger, on_event, rpc, rpc_error
from kontiki.task.task import task
from kontiki.web import http


class TestServiceDelegate(ServiceDelegate):
    def __init__(self):
        self._retry = False


class TestHttpRequestModel(BaseModel):
    name: str
    age: int


class TestHttpExampleError(Exception):
    pass


class TestService:
    messenger = Messenger()
    delegate = TestServiceDelegate()

    http_error_handlers = {TestHttpExampleError: (499, "Example error occurred")}

    # ------------------------------------------------------------
    # RPC methods
    # ------------------------------------------------------------

    @rpc
    async def rpc_example(self, feature):
        if feature == "standard_case":
            return "Standard case"
        elif feature == "user_input_error":
            return rpc_error("USER_INPUT_ERROR", "User input error")
        elif feature == "server_error":
            raise RuntimeError("Unexpected Server error")

    @rpc(include_headers=True)
    async def rpc_with_headers(self, _headers):
        return _headers["user_header"]

    # ------------------------------------------------------------
    # Events
    # ------------------------------------------------------------

    @on_event("simple_event")
    async def on_simple_event(self, payload):
        await self.messenger.publish("simple_event_processed", payload)

    @on_event("tests.event.name", use_config=True)
    async def on_dynamic_event_name(self, payload):
        await self.messenger.publish("dynamic_event_name_processed", payload)

    @on_event("retry_ok", requeue_on_error=True, reject_on_redelivered=True)
    async def on_retry_ok(self, payload):
        if not self.delegate._retry:
            self.delegate._retry = True
            raise RuntimeError("Retry should be enabled")
        if self.delegate._retry:
            await self.messenger.publish("retry_ok_processed", payload)

    @on_event("broadcast_off")
    async def on_broadcast_off(self, payload):
        await self.messenger.publish("broadcast_off_processed", payload)

    @on_event("broadcast_on", broadcast=True)
    async def on_broadcast_on(self, payload):
        await self.messenger.publish("broadcast_on_processed", payload)

    # ------------------------------------------------------------
    # Http
    # ------------------------------------------------------------

    @http("/test_http", "GET")
    async def test_http(self, request):
        return web.json_response({"message": "Hello, from test_http!"})

    @http("tests.http.entrypoint", "GET", use_config=True)
    async def test_http_entrypoint_from_config(self, request):
        return web.json_response(
            {"message": "Hello, from test_http_entrypoint_from_config!"}
        )

    @http(
        "/test_http_with_request_model",
        "POST",
        request_model=TestHttpRequestModel,
        validate_request=True,
    )
    async def test_http_with_request_model(self, request, body: TestHttpRequestModel):
        return web.json_response(
            {"message": "Hello, from test_http_with_request_model!"}
        )

    @http("/test_http_fail", "GET", errors=[TestHttpExampleError])
    async def test_http_fail(self, request):
        raise TestHttpExampleError()


class TaskService:
    messenger = Messenger()

    # ------------------------------------------------------------
    # Tasks
    # ------------------------------------------------------------

    @task(interval=10, immediate=True)
    async def task_immediate(self):
        await self._publish("task_immediate_processed")

    @task(interval=10, immediate=False)
    async def task_not_immediate(self):
        await self._publish("task_not_immediate_processed")

    async def _publish(self, msg):
        await self.messenger.publish(msg, msg)
