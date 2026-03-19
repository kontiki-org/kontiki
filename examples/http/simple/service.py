import logging

from pydantic import BaseModel

from kontiki.web import http


class HelloRequest(BaseModel):
    name: str | None = None


class HelloResponse(BaseModel):
    message: str


class EchoRequest(BaseModel):
    message: str


class EchoResponse(BaseModel):
    message: str


class HttpExampleError(Exception):
    """Custom error used to demonstrate HTTP error mapping."""


class SimpleHttpService:
    """Simple HTTP-only service showcasing Kontiki's @http entrypoints."""

    name = "SimpleHttpService"

    # Map HttpExampleError to HTTP 400 with a custom message.
    http_error_handlers = {
        HttpExampleError: (400, "Example error occurred"),
    }

    @http(
        "/health",
        "GET",
        version="v1",
        summary="Health check",
        description="Basic health endpoint returning a static status.",
        tags=["health"],
        response_model=HelloResponse,
    )
    async def health(self, request):
        logging.info("Health endpoint called")
        return HelloResponse(message="ok").model_dump()

    @http(
        "app.http.ping_path",
        "GET",
        use_config=True,
        version="v1",
        summary="Ping (path from config)",
        description="Path is resolved from config (use_config=True). Use your own config namespace, not kontiki.*",
        tags=["health"],
        response_model=HelloResponse,
    )
    async def ping(self, request):
        logging.info("Ping endpoint called (path from config)")
        return HelloResponse(message="pong").model_dump()

    @http(
        "/hello",
        "POST",
        version="v1",
        summary="Hello endpoint",
        description="Greets the user with an optional name.",
        tags=["hello"],
        request_model=HelloRequest,
        response_model=HelloResponse,
        validate_request=True,
    )
    async def hello(self, request, body: HelloRequest):
        name = body.name or "world"
        logging.info("Hello endpoint called with name=%s", name)
        return HelloResponse(message=f"Hello, {name}!").model_dump()

    @http(
        "/echo",
        "POST",
        version="v1",
        summary="Echo endpoint",
        description="Echoes back the provided message.",
        tags=["echo"],
        request_model=EchoRequest,
        response_model=EchoResponse,
        validate_request=True,
    )
    async def echo(self, request, body: EchoRequest):
        logging.info("Echo endpoint called with message=%s", body.message)
        return EchoResponse(message=body.message).model_dump()

    @http(
        "/fail",
        "GET",
        version="v1",
        summary="Failure endpoint",
        description="Always raises a custom HttpExampleError to demonstrate error mapping.",
        tags=["errors"],
        errors=[HttpExampleError],
    )
    async def always_fail(self, request):
        logging.info("always_fail endpoint called, raising HttpExampleError")
        raise HttpExampleError("This is a demo error mapped to HTTP 400.")
