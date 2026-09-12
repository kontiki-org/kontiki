# Kontiki configuration reference

Framework options live under the **`kontiki`** key. Logging uses a top-level
**`logging`** block (Python dictConfig + Kontiki extensions). Use your own
top-level keys (e.g. `app`) for application settings.

An example file with every option is in [kontiki-config.example.yaml](kontiki-config.example.yaml).

---

## `kontiki.service_name`

| Key | Default | Description |
|-----|---------|-------------|
| `kontiki.service_name` | *(unset)* | Logical service identity for RPC queues and the registry. When unset: class `name` attribute, else the Python class name. |

---

## `kontiki.peers`

Map of peer keys to logical service names for `RpcProxy(..., peer="…")` and
`messenger.open_session(peer="…")`.

| Key | Default | Description |
|-----|---------|-------------|
| `kontiki.peers.<peer>` | *(required if used)* | Target `service_name` for that peer. Missing or empty → fail fast when resolved. |

Example:

```yaml
kontiki:
  peers:
    alert_engine: alert-engine-earth
```

```python
RpcProxy(messenger, peer="alert_engine")
await messenger.open_session(peer="alert_engine")
```

Prefer `peer` for deployment-specific identities; keep a literal `service_name`
for fixed platform targets.

---

## `kontiki.amqp`

| Key | Default | Description |
|-----|---------|-------------|
| `kontiki.amqp.url` | `amqp://guest:guest@localhost/` | AMQP connection URL. |
| `kontiki.amqp.required` | `true` | `true`: fail-fast at start if the broker is unreachable. `false`: the local work (`@task`, `@http`) does not need AMQP and must run even if the broker is down; registry and exception reporting connect when it is up. Distinct from `kontiki.registration.disable`. |
| `kontiki.amqp.rpc.timeout` | `10` | RPC call timeout in seconds. |
| `kontiki.amqp.serialization` | `pickle` | AMQP message format: `pickle` (supported). `json` is deprecated — logs a warning at startup; removal planned in a future major release. |
| `kontiki.amqp.max_pending_messages` | `10` | Consumer prefetch (QoS): max unacknowledged messages per consumer. Limits how many messages a single instance can hold before acknowledging; useful for load balancing and backpressure. |
| `kontiki.amqp.tls` | `{}` | Optional TLS. See below. |

`amqp.required: false` is for work that does not use the bus and must still run
if RabbitMQ is down — typically a periodic `@task` such as a database dump.
When the broker is reachable, the process still registers and reports exceptions
to the registry (TUI / Monitor). `registration.disable: true` never registers.
If both are set, disable wins (no registry client). There is no local buffer:
`publish` / `call` raise while disconnected. Losing the broker after start does
not stop the process.

### `kontiki.amqp.tls`

| Key | Required | Description |
|-----|----------|-------------|
| `enabled` | yes | `true` to enable TLS. |
| `ca_cert` | yes | Path to CA certificate file. |
| `client_cert` | no | Path to client certificate. |
| `client_key` | no | Path to client private key. |

If `enabled` is `false` or missing, or if `amqp.tls` is not a dict, no TLS context is created.

---

## `kontiki.shutdown`

| Key | Default | Description |
|-----|---------|-------------|
| `kontiki.shutdown.grace_seconds` | `25` | Maximum time (seconds) to drain in-flight HTTP handlers, AMQP RPC/event handlers, and the current `@task` iteration before force-close on shutdown. |

---

## `kontiki.registration`

Used when the service registers with a Kontiki registry.

| Key | Default | Description |
|-----|---------|-------------|
| `kontiki.registration.disable` | `False` | Set to `true` to disable registration (never join the registry). Distinct from `kontiki.amqp.required: false`, which still registers once the broker is reachable. |
| `kontiki.registration.delay` | `2` | Delay in seconds before sending the first registration. |
| `kontiki.registration.group` | `business` | Free-form label for UI filters (any string). Blank / whitespace is normalized to `business`. Common conventions: `business`, `platform`. Not a closed set. |
| `kontiki.registration.report_uncaught_exceptions` | `True` | When `true`, uncaught exceptions in RPC, HTTP (unmapped), `@on_event`, and `@task` entrypoints are reported to the registry (same path as `publish_exception`). Set to `false` to opt out. |
| `kontiki.registration.configuration.public_paths` | `None` | List of config paths to expose to the registry (e.g. for UI). If set, only those paths are sent; otherwise no config is sent. |

---

## `kontiki.heartbeat`

| Key | Default | Description |
|-----|---------|-------------|
| `kontiki.heartbeat.interval` | `60` | Interval in seconds between heartbeats sent to the registry. |

---

## `kontiki.http`

For services that expose HTTP entrypoints (`@http`).

| Key | Default | Description |
|-----|---------|-------------|
| `kontiki.http.address` | `0.0.0.0` | Bind address. |
| `kontiki.http.port` | `8080` | Bind port. |
| `kontiki.http.documentation.enabled` | `true` | Whether to register OpenAPI / Swagger endpoints. |
| `kontiki.http.documentation.path_template` | `/api/{version}/docs` | URL path template for docs; `{version}` is replaced by the endpoint version. |
| `kontiki.http.documentation.title` | service name | Title used in OpenAPI. |
| `kontiki.http.documentation.description` | `API documentation for <service name>` | Description used in OpenAPI. |

---

## `logging` (top-level)

Python [`dictConfig`](https://docs.python.org/3/library/logging.config.html)
schema. Kontiki strips its own keys (`directory`), then injects filters and
missing defaults before `dictConfig` runs.

| Key | Default | Description |
|-----|---------|-------------|
| `logging.directory` | *(unset)* | **Recommended** for file logs. When set, every `FileHandler` subclass gets `{directory}/{service_name}-{short_instance_id}.log` (12-hex prefix of the instance UUID). Omit `handlers.*.filename`; an explicit `filename` is ignored (warning). The directory is created if needed. Empty or non-string → fail fast. Without `directory`, explicit `filename` is kept (legacy). |
| `logging.version` | `1` (injected if omitted) | dictConfig version. |
| `logging.disable_existing_loggers` | `true` (injected if omitted) | Explicit `false` is preserved. |
| `logging.formatters` | default formatter if omitted | If omitted, Kontiki injects `default` and assigns it to handlers that have no `formatter`. Custom formatters are left as written. |
| `logging.loggers.kontiki` | `{level: INFO, propagate: true}` if omitted | Keeps framework logs visible when `disable_existing_loggers` is true. |
| `logging.handlers` / `root` | see [example](kontiki-config.example.yaml) | Standard dictConfig. `directory` alone does not create a file handler — declare `FileHandler` / `RotatingFileHandler` / … yourself. |

**Always injected** (not YAML keys):

- Filter `kontiki_flow_id` on every handler — `%(flow_id)s` is `[flow=…]` or `[no flow]`.
- Filter `kontiki_service_identity` on every handler — `%(service_name)s` and `%(short_instance_id)s` on every record. The default line uses `short_instance_id` only; the service name stays in the **filename** (and registry / TUI).

Default line when `formatters` is omitted:

```text
%(asctime)s - %(short_instance_id)s - %(levelname)s - %(flow_id)-19s - %(message)s
```

Unsafe characters in `service_name` become `_` in the file path.

See [advanced-features.md](advanced-features.md) (`logging.directory`, `flow_id`).

---

## Registry server only

The **Kontiki registry** service uses the same `kontiki.*` keys where relevant (e.g. `kontiki.amqp`, `kontiki.http`). In addition, its config supports top-level keys (not under `kontiki`) for its own features:

- **`event_tracker.ttl_minutes`** (default: `0`), **`event_tracker.ttl_hours`** (default: `24 * 7`): event retention.
- **`event_tracker.disable`** (default: `false`): disable event tracking.
- **`event_tracker.cleanup_interval_seconds`** (default: `3600`): cleanup interval.
- **`exception_tracking.*`**: analogous options for exception retention and cleanup.

See the registry example config and source if you run the registry yourself.
