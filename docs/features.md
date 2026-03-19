# Kontiki – Features

Kontiki is a Python microservices framework built on AMQP (aio-pika) and asyncio. 

- **Write only your business logic**: Kontiki manages connections to RabbitMQ, message routing (RPC, events, sessions, broadcast), service lifecycle and configuration merge for you.
- **Run several instances of the same service to scale out**: Kontiki uses asyncio to handle many concurrent requests per process, and you can add more service instances to scale horizontally without dealing with threads yourself.
- **Design service interactions as messages**: combine RPC, events, broadcast and per‑instance sessions to describe how services collaborate, while Kontiki takes care of the AMQP wiring for you.
- **Keep environments aligned**: drive differences between development, staging and production through configuration and a unified way to start services, not ad‑hoc scripts.

This document summarizes the main features Kontiki offers out of the box.

---

## Service structure (recommended)

Keep the **service class** as a thin layer that only exposes entrypoints: methods decorated with `@rpc`, `@on_event`, `@http`, or `@task`. Attach **delegates** as class attributes (objects inheriting from `ServiceDelegate`). The container discovers them, injects itself so they can access config and the service instance, and runs their `setup` / `start` / `stop`. Put your business logic inside delegates; the service methods then only forward calls (e.g. `return await self.delegate.do_something(...)`). The **Messenger** is a delegate too: add it as a class attribute if the service must publish events or call other services via RPC. That way the service class stays focused on wiring entrypoints to delegates, and all domain logic lives in the delegates.

The **service name** used in the registry and for RPC/event routing is the class name by default. To use a user-defined name (e.g. for deployment or to decouple from the class name), set the `name` class attribute.

```python
from kontiki.delegate import ServiceDelegate
from kontiki.messaging import Messenger, on_event, rpc


class MyDelegate(ServiceDelegate):
    async def setup(self):
        # init from self.container.config
        pass

    async def start(self):
        # optional: start background tasks / open connections
        pass

    async def stop(self):
        # optional: stop background tasks / close connections
        pass

    def do_something(self, x):
        # business logic
        return x * 2

    async def handle_thing(self, payload):
        # business logic
        return {"processed": payload}


class MyService:
    name = "compute-api"  # optional: if omitted, the class name "MyService" is used
    delegate = MyDelegate()
    messenger = Messenger()  # delegate: publish events, RPC to other services

    @rpc
    async def compute(self, x):
        return self.delegate.do_something(x)

    @on_event("thing_happened")
    async def on_thing(self, payload):
        result = await self.delegate.handle_thing(payload)
        await self.messenger.publish("thing_processed", result)
```

---

## RPC

RPC in Kontiki is a **synchronous request/reply call over AMQP**: the caller waits for a response, while Kontiki handles routing, correlation, timeouts, and error mapping.

- **Server** : Decorate methods with `@rpc` or `@rpc(include_headers=True)` to expose them. Use `rpc_error("CODE", "message")` to return a client error; let exceptions raise for server errors.
- **Client** : Create a `Messenger` (standalone or from a container), then use `RpcProxy(messenger, service_name="ServiceName")` and call methods on the proxy, or `messenger.call(service_name, method_name, *args, **kwargs)`. Exceptions: `RpcClientError`, `RpcServerError`, `RpcTimeoutError`.
- **Headers** : With `include_headers=True`, the handler receives a `_headers` argument containing AMQP headers.

---

## Events

Events in Kontiki are **asynchronous messages over AMQP**: publishers fire-and-forget, and one or more consumers handle the event depending on the delivery mode (per-service, broadcast, or session-targeted).

- **Handler** : `@on_event("event_type")` or `@on_event("config.key", use_config=True)`. Options:
  - `include_headers=True` : pass message headers to the handler.
  - `requeue_on_error=True` : requeue the message on handler failure.
  - `reject_on_redelivered=True` : reject messages that are redelivered (e.g. after a requeue).
  - `broadcast=True` : every instance of the service receives the event (per-instance queue).
  - `in_session=True` : event is targeted at a specific instance within a session (mutually exclusive with `broadcast`).
- **Publisher** : `messenger.publish(event_type, payload, extra_headers=...)`. Serialization is configurable (default: pickle; can use JSON).

---

## HTTP

HTTP entrypoints are a **built-in façade**: they let you expose and document a small HTTP surface *in the same service and with the same configuration model* as your AMQP entrypoints (validation, error mapping, OpenAPI/Swagger), so you can ship service APIs and operational endpoints without having to add and maintain a separate Flask/FastAPI layer.

- **Routes** : Decorate methods with `@http(path_or_config_key, method, use_config=False, ...)`. Methods receive the aiohttp `request`; for POST/PUT/PATCH with `validate_request=True`, a validated `body` (from `request_model`) is passed as well.
- **Options** : `version`, `summary`, `description`, `tags`, `request_model`, `response_model`, `status_code`, `responses`, `errors`, `skip_documentation`, `validate_request`. Use your own config namespace for paths when `use_config=True`.
- **Error mapping** : On the service class, set `http_error_handlers = {SomeError: (status_code, "message")}`. List exception types in `errors=[...]` on the decorator for documentation. When a handler raises a mapped exception, the response is the configured status and body.
- **Documentation** : OpenAPI and Swagger UI are registered automatically when `http.documentation.enabled` is true (path template and title/description are configurable under `kontiki.http.documentation`).

---

## Sessions (targeted events)

To send events to a **specific service instance** without managing reply_to and instance ids yourself:

1. **Open a session** : `session = await messenger.open_session("ServiceName")`. This performs an internal RPC handshake and returns an `EventSession`.
2. **Publish in session** : `await session.publish("event_type", payload)`. Events are routed to that instance and carry a session id in headers.

Handlers that should receive session-scoped events use `@on_event("event_type", in_session=True, include_headers=True)`.

---

## Tasks (periodic)

Tasks in Kontiki are **scheduled coroutines**: the container runs them on a fixed interval in the service event loop, so you can implement periodic work without an external scheduler.

- **`@task(interval=seconds, immediate=True|False)`** : Registers a method to be run periodically. `immediate=True` runs it once at startup, then on the interval. The method can be async.

---

## Running a service

**Recommended: executable via `cli.run`**

Expose your service as a CLI command (like the Kontiki registry) so users run a single executable with `--config`:

1. In your package, call `cli.run` from an entry function:

```python
# e.g. myapp.main
from kontiki.runner import cli
from myapp.service import MyService

def run():
    cli.run(
        MyService,
        "Description of my service.",
        version="1.0.0",
        disable_service_registration=False,  # optional
    )
```

2. Declare the script in `pyproject.toml`:

```toml
[tool.poetry.scripts]
my_service = "myapp.main:run"
```

After `poetry install` (or `pip install`), the command `my_service --config config.yaml [--config other.yaml]` is available. The runner parses `--config` (required, repeatable), then starts the service class; methods decorated with `@rpc`, `@on_event`, `@http`, `@task` are discovered and registered automatically.

**Alternative: direct runner**

Without defining a script, you can start any service class with:

```bash
python -m kontiki.runner.__main__ <module.path.ServiceClass> --config config.yaml [--config other.yaml] [--version 1.0.0] [--disable-service-registration]
```

---

## Configuration

- **Merge** : Multiple YAML config files can be merged (later files override earlier ones). Use `--config file1.yaml --config file2.yaml` when starting a service.
- **Parameters** : `get_parameter(config, "path.to.key", default)` and `get_kontiki_parameter(config, "amqp.url", default)` read from the merged config using **dot-separated paths** (e.g. `app.http.port`). Use your own namespace (e.g. `app.*`) for application settings; **do not use the `kontiki.*` namespace** for your own keys.
- **Paths from config** : For HTTP routes and event types, you can pass a config key and set `use_config=True` so the value is read from config at startup (e.g. different paths per environment).

---

## Service registry (optional)

If the Kontiki registry service is running and registration is not disabled, the service registers itself and can:

- **Heartbeats** : Sent automatically at a configurable interval.
- **Degraded state** : Decorate a method with `@degraded_on`; it is called at each heartbeat. If it returns `True`, the service is reported as degraded. Use your own logic (e.g. error count, dependency health).
- **Event / exception tracking** : The registry can record events and reported exceptions for observability. Clients can call `ServiceRegistryProxy(messenger).get_services()`, `get_events()`, `get_exceptions()`, and filter by status (e.g. degraded).

If the registry is unavailable at startup, registration is skipped and the service still runs.

---

## Serialization

- **Default** : Pickle. Handlers receive Python objects; `publish` accepts any picklable payload.
- **JSON** : Can be configured (e.g. for interoperability). Request/response models for HTTP can be Pydantic models; the web layer can extract schemas and validate bodies.

---

## Delegates

Services should attach **delegates** (objects inheriting from `ServiceDelegate`) and implement `setup`, `start`, `stop`. The container injects itself and calls these lifecycle methods. Use delegates to keep the service class thin and factor out dependencies (e.g. DB, external APIs) or shared logic.

---

## Testing (helpers)

Kontiki ships with lightweight testing utilities under `kontiki.testing` to help you run **mock services** alongside your system under test (including in synchronous environments like Behave):

- Define a mock service by subclassing `MockService` and using the usual entrypoint decorators (e.g. `@on_event`) to capture calls/events.
- Register mocks in a `MockServiceManager`, then run them in a background thread with `MockServiceRunner`.
- Drive your system and assert on captured inputs:
  - **Events**: store and query emitted events (`event_manager.store_event(...)`, then `manager.get_events("my-mock", wait_for_events=N, timeout=...)`).
  - **HTTP**: record received requests and optionally pre-program responses (`manager.get_http_requests("my-mock")`, `manager.add_http_response("my-mock", response)`).
  - **RPC**: record incoming call arguments and optionally pre-program return values (`manager.get_remote_calls("my-mock")`, `manager.add_remote_return_value("my-mock", value)`), and call your system via `runner.call("service-name", "method_name", ...)`.

For an example of Behave integration tests using these helpers, see [**kontiki-scheduler**](https://github.com/kontiki-org/kontiki-scheduler).
