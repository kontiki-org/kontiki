# Advanced features

Kontiki’s surface looks small: `@http`, `@rpc`, `@on_event`, `@task`.
Most of the leverage sits one layer deeper. This page groups some of the **advanced
features** that are easy to miss and worth knowing early.


## Mental model

| Need | Reach for |
|------|-----------|
| Sync API | `@http` / `@rpc` |
| Async reaction | `@on_event` |
| Time-driven work | `@task` |
| Fleet health | registry + `degraded_on` |
| Orchestrator liveness | `GET /live/{service_name}` |
| Separate business vs platform in KontikiTUI | `kontiki.registration.group` |
| Crash visibility | let exceptions propagate |
| Expected RPC failures | `rpc_error` + `RpcClientError.code` |
| Retry event once then stop | `requeue_on_error` + `reject_on_redelivered` |
| Cross-service debug | `flow_id` → filter in KontikiTUI Logs |
| Route by business field | encode it in `event_type` |
| Env-specific event names | `@on_event(..., use_config=True)` |
| One handler, several exact types | `@on_event([...])` or config list |
| Same binary, distinct RPC / registry identity | `kontiki.service_name` |
| RPC peer from deployment config | `RpcProxy(..., peer="…")` → `kontiki.peers` |
| Tests on the bus | `kontiki.testing` |
| Consistent logs / shared defaults | multi `--config` merge |
| Uniform process entrypoint | `kontiki.runner.cli.run` |
| Call Kontiki from FastAPI / etc. | standalone `Messenger` |

---

## Fleet & health

### Service registry & heartbeats

**When:** You want a live picture of the fleet — which instances exist, and
whether each is `active`, `degraded`, or `down`.

Run the **registry** as its own Kontiki service. Every other service then
**registers and heartbeats automatically** (unless registration is disabled).
Miss enough heartbeats → the registry marks the instance `down`. No
application code required for the happy path.

Day to day you browse that picture in **[KontikiTUI](https://github.com/kontiki-org/kontiki-tui)**
(services, registry events / exceptions, log tails) or via orchestrator probes —
not from business code. RPC queries on the registry exist for tooling, but most
services never call them.

#### `GET /live/{service_name}`

**When:** Docker Compose / Kubernetes (or any orchestrator) needs a readiness /
liveness URL for a service that may be bus-only (no useful HTTP of its own).

The registry exposes:

```http
GET /live/{service_name}
```

- **200** — at least one instance of that name is `active` or `degraded` (recent
  heartbeat)
- **503** — none alive

Prefer this over probing each worker’s own HTTP port. When `{service_name}` is
the registry itself, **200** means the registry HTTP server is up (no
self-registration required).

#### `kontiki.registration.group`

**When:** KontikiTUI should distinguish day-to-day workloads from platform /
mesh services (registry, gateways, …) without inventing a second registry.

```yaml
kontiki:
  registration:
    group: platform   # default: business
```

Typical values: `business` (workloads) and `platform` (ops). Blank → `business`.
KontikiTUI filters on this field; registry RPC and `/live/...` still see the
**full** fleet — group is a label, not a visibility wall.

**Gotcha:** The bus keeps working without a registry. What you lose is fleet
visibility (and anything built on it: degraded signals, live probes,
exception aggregation).

---

### `degraded_on` — health from business logic

**When:** A dependency is failing repeatedly (SMTP, Telegram API, upstream HTTP)
and you want the instance marked degraded in the registry — ideally with a short
**reason** for alerting.

```python
from kontiki.registry import degraded_on

class EmailNotifierService:
    ...

    @degraded_on
    def is_degraded(self):
        # Legacy: return True / False
        # Prefer: (True, reason) so registry.instance.status_changed carries it
        if self.delegate.smtp_failing():
            return True, "smtp unreachable"
        return False
```

Heartbeats carry that signal. On transition to `degraded`,
`registry.instance.status_changed` includes optional `reason` (not stored on
`get_services` — alerting is event-driven). KontikiTUI (or an alerting pipeline
on those status events) can react without scraping logs.

**Gotcha:** `degraded_on` reports health — it does not retry or fix the dependency.
Returning plain `True` still works; `reason` is then `null` on the event.

---

### Uncaught exceptions → registry

**When:** You want failures on HTTP / RPC / tasks to be visible fleet-wide without
hand-rolling error publishers.

Kontiki can report uncaught exceptions to the registry (`registry.exception` /
exception tracking). Leave domain errors you expect to map (validation, auth)
as controlled responses; let unexpected failures bubble.

```python
# Prefer: let unexpected errors propagate
@on_event("telegram.alerting.notification.requested")
async def on_notification_requested(self, payload):
    await self.delegate.send_notification_telegram(payload)
```

**Gotcha:** Catching everything and only logging locally hides the failure from
the registry and from any alerting built on top of it.

---

## Controlled failures

### `rpc_error` — expected failures with a stable code

**When:** The caller did something wrong or hit a business rule (bad input,
not found, conflict). You want a **controlled** failure the client can branch
on — not an uncaught exception / `INTERNAL_ERROR`.

**Server** — return `rpc_error(code, message)` instead of raising:

```python
from kontiki.messaging import rpc, rpc_error

@rpc
async def get_user(self, user_id):
    user = await self.delegate.find(user_id)
    if user is None:
        return rpc_error("NOT_FOUND", f"No user {user_id}")
    if not user.active:
        return rpc_error("USER_INACTIVE", "User is inactive")
    return user
```

**Client** — catch `RpcClientError` and switch on `e.code`:

```python
from kontiki.messaging import RpcClientError, RpcServerError, RpcProxy

users = RpcProxy(messenger, service_name="user-service")

try:
    user = await users.get_user(user_id)
except RpcClientError as e:
    if e.code == "NOT_FOUND":
        return None  # or 404 in an HTTP gateway
    if e.code == "USER_INACTIVE":
        raise PermissionError(e.message)
    raise  # unknown client code — fail closed
except RpcServerError as e:
    # Unexpected: bug, dependency down → e.code often INTERNAL_ERROR
    # Logged/reported server-side; retry or surface 502
    raise
```

| Path | How | Client sees | Registry uncaught? |
|------|-----|-------------|--------------------|
| Business / validation | `return rpc_error("CODE", "…")` | `RpcClientError` + `e.code` | No |
| Unexpected bug | `raise …` (unhandled) | `RpcServerError` / `INTERNAL_ERROR` | Yes (if enabled) |

**Gotcha:** Raising a domain exception without mapping still becomes a **server**
error. Use `rpc_error` for anything the caller is expected to handle. Keep codes
stable (`NOT_FOUND`, `VALIDATION_ERROR`, …) — they are your RPC API contract.

---

### Deployment identity — `kontiki.service_name` and `RpcProxy(peer=…)`

**When:** The same binary must run as several logical services on one mesh
(plans, regions, blast-radius splits) without cloning the codebase.

**Host** — set the identity in YAML (priority: config > class `name` > class name):

```yaml
kontiki:
  service_name: alert-engine-earth
```

RPC queues become `{service_name}.{method}`; the registry sees that name. Do
**not** use this for simple HA (keep the same name, multiple instances).

**Caller** — prefer a peer key over a hardcoded name so deploys stay config-only:

```yaml
kontiki:
  peers:
    alert_engine: alert-engine-earth
```

```python
alerts = RpcProxy(messenger, peer="alert_engine")  # → kontiki.peers.alert_engine
await alerts.compute(...)
```

Use `RpcProxy(messenger, service_name="ServiceRegistry")` for **fixed** platform
targets. `peer` and `service_name` are mutually exclusive; missing
`kontiki.peers.<peer>` fails fast when the proxy resolves. Standalone messengers
have no container conf — bind a service messenger (or pass `service_name`) for
`peer`.

**Gotcha:** Host override and caller peers must agree on the same logical name.
Changing either side requires a restart so queues / resolution pick up the value.

---

### HTTP error mapping

**When:** Domain exceptions should become stable HTTP status codes.

```python
class AlertEngineService:
    http_error_handlers = {
        ValidationError: (422, ValidationError.message),
        AuthError: (401, AuthError.message),
    }

    @http("/alerts", "POST", errors=[ValidationError, AuthError])
    async def post_alert(self, request):
        ...
```

**Gotcha:** Unmapped exceptions become 500 and can be reported as uncaught
exceptions (see above).

---

## Messaging

### Headers on the bus

**When:** You need request metadata (auth tokens, custom ids) alongside the
payload — without stuffing it into the body.

Outbound:

```python
await self.messenger.publish(
    "alert.normalized",
    alert,
    extra_headers={"tenant": "ops"},
)
await proxy.some_method(arg, extra_headers={"tenant": "ops"})
```

Inbound:

```python
@on_event("alert.normalized", include_headers=True)
async def on_alert(self, payload, _headers=None):
    tenant = (_headers or {}).get("tenant")
```

Same idea for `@rpc(..., include_headers=True)`.

**Gotcha:** Headers other than `flow_id` are **not** propagated automatically
across hops. Whatever custom metadata you need downstream must be passed again
on the next `publish` / `call`. `flow_id` is the exception — Kontiki propagates
it via ContextVar + `kontiki_flow_id` (see below).

Kontiki already adds its own headers (`kontiki_service_name`, `kontiki_instance_id`,
`kontiki_flow_id`, …). Do not confuse those with AMQP `correlation_id` (used for
RPC reply matching).

---

### Dynamic routing via `event_type`

**When:** The same logical message must reach **different services** depending on a
business field (channel, tenant, region…) — without a central switch/case in the
publisher.

Kontiki routes events by **routing key = `event_type`**. Put the discriminator
**in the event type string**; each consumer binds only the keys it owns.

```python
# Publisher — one loop, no if/elif on channel
for request in notification_requests:
    event_type = f"{request.channel}.alerting.notification.requested"
    await messenger.publish(event_type, request)

# email-notifier-service
@on_event("email.alerting.notification.requested")
async def on_email(self, payload):
    await self.delegate.send_email(payload)

# telegram-notifier-service
@on_event("telegram.alerting.notification.requested")
async def on_telegram(self, payload):
    await self.delegate.send_telegram(payload)
```

```mermaid
flowchart LR
  AE[alert-engine]
  AE -->|email.alerting…requested| Email[email-notifier]
  AE -->|telegram.alerting…requested| Tg[telegram-notifier]
```

Other shapes:

- `tenant.{id}.orders.created` — isolate noisy tenants
- `region.eu.inventory.updated` — geo-split consumers
- `priority.high.jobs.run` vs `priority.low.jobs.run` — separate worker pools

**Gotcha:** Agree on a naming convention (`{discriminator}.{domain}.{action}`) and
keep the set of discriminators bounded (or document how new ones are onboarded).
A typo in the prefix is a silent miss — no consumer, no error on publish.
This is routing, not filtering inside one handler: prefer distinct event types
over one event + `if payload.channel == ...`.

#### Several exact event types on one handler

**When:** One handler should react to a small set of related types (or the set
varies by environment) without wildcards or a shared catch-all queue.

```python
@on_event(["order.created", "order.updated"])
async def on_order_change(self, payload):
    ...

@on_event("app.events", use_config=True)
async def on_configured_events(self, payload):
    ...
```

```yaml
app:
  events:
    - order.created
    - order.updated
```

**Use case (list from config):** same image, several deployments — each YAML
lists only the types that pool should consume (e.g. orders vs billing). No
rebuild; pools do not compete on each other’s messages.

Pass a **list of exact type strings**, or resolve one from config (`use_config=True`
→ string or list). Kontiki declares **one durable queue and one TOPIC bind per
type**; options (`broadcast`, `in_session`, `requeue_on_error`, …) apply to every
type in the list.

**Gotcha:** Empty list → fail fast at startup. No TOPIC wildcards (`*`, `#`) and
no application-level regexp — only exact types. Two handlers on the **same**
`service_name` must not subscribe to the same type (they would compete on one
queue).

#### Event type from configuration (`use_config=True`)

**When:** The routing key must be environment-specific (prefix, tenant, stage)
without rebuilding the image — put it in YAML and resolve at bind time. The
resolved value may be a **single string** or a **list of strings** (see above).

```python
@on_event("app.events.order_created", use_config=True)
async def on_order_created(self, payload):
    ...
```

```yaml
# staging
app:
  events:
    order_created: staging.orders.created

# production
app:
  events:
    order_created: orders.created
```

The first argument is a **config path** (dot-separated), not the literal event
name. At startup Kontiki reads that path and binds the queue(s) to the resolved
value. Same pattern exists for `@http(..., use_config=True)` (path from config)
and config-driven `@task` intervals.

**Gotcha:** Missing path → startup failure (`ConfigParameterError`). Publishers
must use the **same** resolved name(s) (share the key, or document the contract).
Changing the YAML value requires a **restart** so the queue is rebound.

---

### `flow_id` — correlate a path in logs

**When:** You need to follow one business flow across services without opening
every log file by hand.

```python
await messenger.publish("alert.normalized", alert, flow_id=alert.alert_id)
# or omit flow_id → Kontiki generates a 12-hex id and propagates it
```

Logs then carry something like (filter sets the whole field, including brackets):

```text
… - [flow=a1b2c3d4e5f6] - Message received on alert.normalized
… - [flow=a1b2c3d4e5f6] - Call: get_recipients_for_alert(...)
… - [no flow] - Polling USGS ...
```

**Day to day:** in [KontikiTUI](https://github.com/kontiki-org/kontiki-tui) →
**Logs** tab, filter on the id (e.g. `a1b2c3d4e5f6` or `[flow=a1b2c3d4e5f6]`).
lnav aggregates the files under `logs.directory`, so you see the whole path in
one place.

**Gotcha:** Custom logging YAML is not rewritten — add `%(flow_id)s` yourself if
you want it visible. Until a flow starts (idle `@task`), lines show `[no flow]`.

---

### `@on_event` delivery modes

Three modes. Default first — the one you want most of the time — then the two
special cases.

**Same service vs different services:** delivery modes below talk about
**instances of one service** (replicas). Separately: if **two different
services** both `@on_event("same.event")`, each has its own queue
(`{service}.{event}.queue`), so **both services receive a copy** — then within
each service, default / broadcast / session applies to that service’s instances.

```mermaid
flowchart TB
  Pub[Publisher] --> E[same.event]
  E --> Q1[("email-notifier.same.event.queue")]
  E --> Q2[("telegram-notifier.same.event.queue")]
  Q1 --> EN[email-notifier<br/>instances compete or fan-out]
  Q2 --> TN[telegram-notifier<br/>instances compete or fan-out]
```

```mermaid
flowchart LR
  subgraph S["Service X — three instances"]
    A1[X #A]
    A2[X #B]
    A3[X #C]
  end
  P[Publisher]
  P -->|default| Q1[(X shared queue)]
  Q1 --> A1
  Q1 -.-> A2
  Q1 -.-> A3
  P -->|broadcast| QA[(queue · X #A)]
  P -->|broadcast| QB[(queue · X #B)]
  P -->|broadcast| QC[(queue · X #C)]
  QA --> A1
  QB --> A2
  QC --> A3
  P -->|in_session| QS[(queue · X #B)]
  QS --> A2
```

*(Dotted = competing consumers: one winner per message among instances of X.
Broadcast = every instance of X. Session = one pinned instance of X.)*

#### Default — one shared queue, competing consumers

**What it does:** All **instances of this service** share **one** queue bound to
the event type. Each message is delivered to **exactly one** instance
(load-balanced by the broker).

```python
@on_event("alert.normalized")
async def on_alert(self, payload):
    await self.delegate.handle(payload)
```

```mermaid
flowchart LR
  Pub[Publisher] --> E[alert.normalized]
  E --> Q[("alert-engine.alert.normalized.queue")]
  subgraph AE["alert-engine"]
    W{one winner}
    A["instance A"]
    B["instance B"]
    C["instance C"]
  end
  Q --> W
  W --> A
  W -.-> B
  W -.-> C
```

**When:** Do this job once — send a notification, write a row, run a workflow
step. Scale out by adding instances; throughput goes up, side effects stay
once-per-message.

**Gotcha:** Do not put per-instance local state updates here (cache drop,
reload). Only one replica would see the event — use `broadcast` for that.

#### `broadcast=True` — every instance must see the event

**What it does:** Each **instance of this service** binds its **own** queue to
the event. A single publish is delivered to **all** running instances of that
service (fan-out), not to just one worker.

**Use cases:**

1. **Local cache invalidation** — Config or catalog changed; every replica must
   drop its in-memory cache, not only one lucky instance.
2. **Warm / reload signal** — “Reload rules from disk”, “rotate credentials”:
   each process applies the change locally.
3. **Presence / liveness side effects** — e.g. each instance refreshes a local
   metric gauge or reconnects a sidecar when `platform.reconfigure` fires.

```python
@on_event("catalog.changed", broadcast=True)
async def on_catalog_changed(self, payload):
    await self.delegate.reload_local_cache()
```

```mermaid
flowchart TB
  Pub[Publisher] --> E[catalog.changed]
  subgraph Cat["catalog-service"]
    QA[("…queue · instance A")]
    QB[("…queue · instance B")]
    QC[("…queue · instance C")]
    A["instance A<br/>reload cache"]
    B["instance B<br/>reload cache"]
    C["instance C<br/>reload cache"]
  end
  E --> QA --> A
  E --> QB --> B
  E --> QC --> C
```

**Gotcha:** N instances ⇒ N deliveries ⇒ N side effects. Do not use broadcast
for “do this job once” (send email, write DB row). That belongs on the default
competing queue.

#### `in_session=True` — talk to one specific instance

**What it does:** The handler queue binds to `event_type.<instance_id>`.
Clients first `open_session(service_name)` (RPC), then publish through the
returned `EventSession`, which routes to **that instance of that service** and
attaches a `kontiki_session_id` header.

**Use cases:**

1. **Sticky interactive client** — A TUI / admin UI opens a session to one
   backend instance and streams UI-specific events (progress, prompts) only
   there, so replies and state stay on the same process.
2. **Per-connection push** — WebSocket gateway or long-lived agent pinned to
   instance X; only X should receive `user.notify` for that connection.
3. **Debug / operator attach** — “Attach to instance `abc` and dump its local
   state” without waking every replica.

```python
# Service — only the targeted instance runs this handler
@on_event("ui.progress", in_session=True)
async def on_ui_progress(self, payload):
    await self.delegate.forward_to_local_client(payload)


# Client — pin to one instance, then publish into that session
session = await messenger.open_session("ui-gateway-service")
await session.publish("ui.progress", {"pct": 40})
```

```mermaid
sequenceDiagram
  participant C as Client
  participant Bus as AMQP
  participant A as ui-gateway #A
  participant B as ui-gateway #B

  C->>Bus: open_session(ui-gateway-service)
  Bus->>B: handshake RPC
  B-->>C: instance_id=B, session_id
  Note over A: same service, other instance — ignores
  C->>Bus: publish ui.progress.B
  Bus->>B: only #B in_session queue
  B-->>B: forward to local client
```

**Gotcha:** `in_session` and `broadcast` cannot both be true. If the target
instance dies, session publishes will not be picked up by another replica —
the client must open a new session.

---

### Event delivery: `requeue_on_error` and `reject_on_redelivered`

**When:** A handler can fail transiently (downstream timeout) and you want **one
retry** from the broker, then give up instead of looping forever.

```python
@on_event(
    "jobs.run",
    requeue_on_error=True,
    reject_on_redelivered=True,
)
async def on_job(self, payload):
    await self.delegate.run_job(payload)  # may raise
```

What happens:

1. **First failure** + `requeue_on_error=True` → message is requeued (broker
   delivers again, typically with `redelivered=True`).
2. **Second failure** on that redelivery + `reject_on_redelivered=True` → message
   is **rejected** (not requeued again) → stops the poison loop.

```mermaid
sequenceDiagram
  participant B as Broker
  participant H as Handler
  B->>H: deliver #1
  H--xB: raise
  Note over B: requeue
  B->>H: deliver #2 (redelivered)
  H--xB: raise
  Note over B: reject — stop
```

Use both flags together for “retry once then drop”. Use only `requeue_on_error`
if you accept unbounded retries (usually you do not). Leave both off (default)
when failures should not bounce the message (e.g. bad payload — fix publisher).

**Gotcha:** Requeue does not fix poison data. Prefer validating early and using
`rpc_error`-style discipline on the producer when possible. Rejected messages
are not a dead-letter queue unless you configure one in RabbitMQ.

---

## Running services

### `@task` — periodic work that stays in Kontiki

**When:** Polling, sweeps, or other timer-driven logic that belongs to a service.
The work keeps the same process, logs, registry health, messaging, and config as
the rest of the service.

```python
@task(interval="app.poll_interval_seconds", immediate=True)
async def poll(self):
    ...
```

With config keys (see `@task` / `resolve_task_interval`), the interval can come
from YAML.

**Gotcha:** Invalid or missing config should fail loudly at startup — prefer
that over silent fallbacks in production paths.

---

### Config file merge — one logging style, many services

**When:** You run several services and want identical log format / handlers,
without copy-pasting a `logging:` block into every YAML.

Pass multiple `--config` files; Kontiki deep-merges them (nested dicts overlay;
conflicting leaf values fail at startup).

Put the shared logging shape in a common file. In each service file, set **only**
the log filename (and any true per-service knobs).

```yaml
# common.services.yaml — used by every service
kontiki:
  amqp:
    url: amqp://guest:guest@rabbitmq/

logging:
  version: 1
  disable_existing_loggers: true
  formatters:
    default:
      format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  handlers:
    file:
      class: logging.FileHandler
      formatter: default
      level: DEBUG
  root:
    handlers: ["file"]
    level: DEBUG
```

```yaml
# alert_engine.yaml — service-specific
logging:
  handlers:
    file:
      filename: /data/alert_engine_service.log

kontiki:
  http:
    port: 8005
```

```bash
kontiki-runner myapp.AlertEngineService \
  --config common.services.yaml \
  --config alert_engine.yaml
```

Same pattern for AMQP URL, registration defaults, etc.: declare once in common,
override leaves only where a service truly differs.

**Gotcha:** Redefining the same leaf with a *different* value in two files raises
`ConfigMergeError`. Prefer “common owns the structure; service owns the path”.
Do not duplicate the full formatter block in every service file “just in case”.

---

### `cli.run` — one way to start every service

**When:** You want all services launched the same way (local, Docker, Compose,
Poetry scripts) instead of each reinventing argparse.

```python
# myapp/alert_engine/main.py
from kontiki.runner import cli
from myapp.alert_engine.service import AlertEngineService

def run():
    cli.run(
        AlertEngineService,
        "Alert Engine service.",
        version="0.1.0",
    )

if __name__ == "__main__":
    run()
```

```toml
# pyproject.toml
[tool.poetry.scripts]
myapp-alert-engine = "myapp.alert_engine.main:run"
```

```bash
myapp-alert-engine \
  --config common.services.yaml \
  --config alert_engine.yaml
```

Every service gets the same CLI: repeatable `--config` flags, merge order =
argument order, same runner lifecycle (logging, messaging, registry, HTTP, tasks).

**Gotcha:** `--config` is required at least once. Put shared defaults in the first
file, service overrides in the next — same merge rules as above.

---

## Beyond a service

### Standalone `Messenger` — gateway into Kontiki from anywhere

**When:** You already have an API in FastAPI, Django, Flask, a worker, a notebook…
and you do **not** want to rewrite it as a Kontiki service — but you want that
code to talk to Kontiki backends (RPC + events) on the same bus.

Standalone `Messenger` is the bridge: same `publish` / `RpcProxy` API as inside a
service, without `@http` / registry / the full container.

```python
from kontiki.messaging import Messenger, RpcProxy

async with Messenger(
    amqp_url="amqp://guest:guest@localhost/",
    standalone=True,
    client_name="edge-api",
) as messenger:
    await messenger.publish("alert.normalized", alert)
    subscription = RpcProxy(messenger, service_name="subscription-service")
    recipients = await subscription.get_recipients_for_alert(alert=alert)
```

Wire `start` / `stop` (or `async with`) into your host framework’s lifecycle
(FastAPI lifespan, Django startup, etc.).

Other fits:

- **CLI / batch / external schedulers** — kick a Kontiki pipeline without embedding the service
- **Migration path** — grow Kontiki backends gradually; edge stays on your current stack
- **Tests / scripts** — one-shot publish/call against a live broker

**Gotcha:** Standalone is a **client**, not a service: no `@on_event` consumer, no
heartbeat registration unless you build that yourself. The broker must be up.
Prefer one long-lived messenger per process, not a new connection per request.

---

### Integration testing helpers

**When:** Behave / integration tests need fake peers on the bus.

```python
from kontiki.testing import MockService, MockServiceManager, MockServiceRunner
from kontiki.messaging import on_event, rpc

class SubscriptionServiceMock(MockService):
    name = "subscription-service"

    @rpc
    async def get_recipients_for_alert(self, alert):
        self.remote_call_manager.store_call_args(alert)
        return self.remote_call_manager.get_return_value()
```

Queue return values with `manager.add_remote_return_value(...)`, assert with
`get_remote_calls` / `get_events` / `get_http_requests`.

**Gotcha:** Return values are a FIFO. Exhausting the queue raises
`No more values to return` — leftover bus traffic can consume presets if the
broker is shared with other publishers.
