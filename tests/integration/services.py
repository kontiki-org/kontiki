from aiohttp import web
from pydantic import BaseModel

from kontiki.delegate import ServiceDelegate
from kontiki.messaging import Messenger, on_event, rpc, rpc_error
from kontiki.messaging.publisher.rpc import RpcProxy
from kontiki.registry import degraded_on
from kontiki.task.task import task
from kontiki.web import http


class TaskServiceDelegate(ServiceDelegate):
    def __init__(self):
        self._count = 0


class TestServiceDelegate(ServiceDelegate):
    def __init__(self):
        self._attempts = 0
        self._drop_attempts = 0


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

    @on_event(["multi_event_a", "multi_event_b"])
    async def on_multi_event_literal(self, payload):
        await self.messenger.publish("multi_event_literal_processed", payload)

    @on_event("tests.event.list", use_config=True)
    async def on_multi_event_from_config(self, payload):
        await self.messenger.publish("multi_event_config_processed", payload)

    @on_event("retry_ok", max_attempts=4)
    async def on_retry_ok(self, payload):
        self.delegate._attempts = self.delegate._attempts + 1
        if self.delegate._attempts < 4:
            raise RuntimeError(f"Attempt #{self.delegate._attempts} failed")
        else:
            await self.messenger.publish("retry_ok_processed", payload)

    @on_event("retry_drop", max_attempts=2)
    async def on_retry_drop(self, payload):
        self.delegate._drop_attempts = self.delegate._drop_attempts + 1
        await self.messenger.publish("retry_drop_attempt", payload)
        raise RuntimeError(f"retry_drop attempt #{self.delegate._drop_attempts}")

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


class ServiceNameTestService:
    """Minimal service for kontiki.service_name override checks."""

    messenger = Messenger()

    @rpc
    async def rpc_example(self, feature):
        if feature == "standard_case":
            return "Standard case"
        raise RuntimeError(f"Unexpected feature: {feature}")


class RpcProxyCallerService:
    """Calls a peer via RpcProxy(peer=...) resolved from kontiki.peers."""

    messenger = Messenger()

    @rpc
    async def call_peer_rpc_example(self, feature):
        peer = RpcProxy(self.messenger, peer="target")
        return await peer.rpc_example(feature)

    @rpc
    async def open_session_peer(self):
        session = await self.messenger.open_session(peer="target")
        return session.service_name


class TaskService:
    messenger = Messenger()
    delegate = TaskServiceDelegate()

    # ------------------------------------------------------------
    # Tasks
    # ------------------------------------------------------------

    @task(interval=10, immediate=False)
    async def task_immediate(self):
        self.delegate._count = self.delegate._count + 1
        await self.messenger.publish("task", f"task#{self.delegate._count}")


class TaskConfigService:
    messenger = Messenger()

    @task("tests.task.interval", immediate=True)
    async def task_from_config(self):
        await self.messenger.publish(
            "task_from_config_processed", "task_from_config_processed"
        )


class RegistryTestServiceDelegate(ServiceDelegate):
    def __init__(self):
        self.degraded = False
        self.degraded_reason = None

    def set_degraded(self, degraded, reason=None):
        self.degraded = degraded
        self.degraded_reason = reason if degraded else None

    def is_degraded(self):
        if not self.degraded:
            return False
        if self.degraded_reason is not None:
            return True, self.degraded_reason
        return True


class RegistryMappedHttpError(Exception):
    pass


class RegistryTestService:
    name = "RegistryTestService"
    delegate = RegistryTestServiceDelegate()
    http_error_handlers = {
        RegistryMappedHttpError: (499, "Mapped error occurred"),
    }

    @rpc
    async def set_degraded(self, degraded, reason=None):
        self.delegate.set_degraded(degraded, reason=reason)

    @rpc
    async def add_test_context(self, **context):
        await self.delegate.add_context(context)

    @rpc
    async def report_test_exception(self):
        try:
            raise Exception("test exception")
        except Exception as e:
            await self.delegate.publish_exception(e)

    @rpc
    async def raise_uncaught_exception(self):
        raise Exception("uncaught rpc exception")

    @http("/raise_uncaught", "GET")
    async def raise_uncaught_http(self, request):
        raise Exception("uncaught http exception")

    @http("/raise_mapped", "GET", errors=[RegistryMappedHttpError])
    async def raise_mapped_http(self, request):
        raise RegistryMappedHttpError("mapped http exception")

    @http("/raise_http_error", "GET")
    async def raise_http_error(self, request):
        raise web.HTTPNotFound()

    @rpc
    async def return_rpc_error(self):
        return rpc_error("CLIENT", "rpc error")

    @degraded_on
    def is_degraded(self):
        return self.delegate.is_degraded()


class FailedReplayService:
    @on_event("job.run", max_attempts=1)
    async def on_job(self, payload):
        raise RuntimeError("job.run failed")


class RegistryUncaughtTaskTestService:
    name = "RegistryTestService"

    @task(interval=10, immediate=True)
    async def raise_uncaught_task(self):
        raise Exception("uncaught task exception")


class DatabaseOps:
    def __init__(self):
        self.count = 0

    @task("app.ticks.interval")
    async def tick(self):
        self.count += 1

    @http("/ticks", "GET")
    async def ticks(self, request):
        return {"count": self.count}
