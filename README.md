<img src="./assets/kontiki_logo.png" width="500">

---
## Overview

**Kontiki** is a Python microservices framework built on **AMQP** (aio-pika) and asyncio.

- **Write only your business logic**: Kontiki manages connections to RabbitMQ, message routing (RPC, events, sessions, broadcast), service lifecycle and configuration merge for you.
- **Design service interactions as messages**: combine RPC, events, broadcast and per‑instance sessions to describe how services collaborate.
- **Configuration‑driven**: merged YAML config and a unified runner (`cli.run`) to start services the same way in development and production.
- **Testability-first API**: integration helpers (`kontiki.testing`) are designed to make end-to-end scenarios easy to express with Behave (mock services, captured events/RPC/HTTP, synchronous test runner).


For a detailed overview of all features, see `docs/features.md`.

---

## Quickstart

Install Kontiki (via pip or Poetry):

```bash
pip install kontiki
```

Define a simple service:

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

def run():
    cli.run(MyService, "Example Kontiki service.", version="0.1.0")
```

Expose it as a CLI command in `pyproject.toml`:

```toml
[tool.poetry.scripts]
my_service = "myapp.main:run"
```

Run your service:

```bash
my_service --config config.yaml
```

> **Kontiki relies on RabbitMQ**. For local development and to run the examples, you can start a RabbitMQ instance via Docker with:
>
> ```bash
> make run-amqp
> ```

---

## Documentation

- Features: `docs/features.md`
- Configuration reference: `docs/configuration.md`
- Example configuration: `docs/kontiki-config.example.yaml`
- Contributing guidelines: `CONTRIBUTING.md`
- License: `LICENSE`

---

## Testing

- Unit/lint/format checks:
  - `make check`
- Integration tests (Behave: HTTP, events, RPC, tasks):
  - `make integration-test`

`integration-test` requires RabbitMQ. Locally, the Makefile target starts it automatically with Docker Compose.

---

## Examples

Examples can be run via the `Makefile` (see targets such as `run-rpc-service`, `run-rpc-example`, `run-simple-events-service`, etc.).

| Feature                                      | Example path                                                     |
|----------------------------------------------|------------------------------------------------------------------|
| Basic RPC                                    | `examples/rpc/`                                                  |
| Simple events                                | `examples/events/simple/`                                        |
| Broadcast events                             | `examples/events/broadcast/`                                     |
| Event serialization                          | `examples/events/serialization/`                                 |
| Session-based events                         | `examples/events/session/`                                       |
| Periodic tasks                               | `examples/task/`                                                 |
| Service registry (admin + client)            | `examples/registry/`                                             |
| Heartbeats & degraded mode                   | `examples/heartbeat/`                                            |
| HTTP entrypoints                             | `examples/http/simple/`                                          |

You can also have a look at the following repository [**kontiki-scheduler**](https://github.com/kontiki-org/kontiki-scheduler). It's an example scheduler service built with Kontiki.

---

## Misc

*Kontiki did not come out of a naming workshop but from the album [*Kontiki*](https://cottonmather.bandcamp.com/album/kontiki) by the band Cotton Mather.  
If you enjoy vintage 4-track indie pop as much as microservices, you should check it out.*
