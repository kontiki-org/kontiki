# Kontiki configuration reference

All framework options live under the **`kontiki`** key. Use your own top-level keys (e.g. `app`) for application settings.

An example file with every option is in [kontiki-config.example.yaml](kontiki-config.example.yaml).

---

## `kontiki.amqp`

| Key | Default | Description |
|-----|---------|-------------|
| `kontiki.amqp.url` | `amqp://guest:guest@localhost/` | AMQP connection URL. |
| `kontiki.amqp.rpc.timeout` | `10` | RPC call timeout in seconds. |
| `kontiki.amqp.serialization` | `pickle` | Serialization for messages: `pickle` or `json`. |
| `kontiki.amqp.max_pending_messages` | `10` | Consumer prefetch (QoS): max unacknowledged messages per consumer. Limits how many messages a single instance can hold before acknowledging; useful for load balancing and backpressure. |
| `kontiki.amqp.tls` | `{}` | Optional TLS. See below. |

### `kontiki.amqp.tls`

| Key | Required | Description |
|-----|----------|-------------|
| `enabled` | yes | `true` to enable TLS. |
| `ca_cert` | yes | Path to CA certificate file. |
| `client_cert` | no | Path to client certificate. |
| `client_key` | no | Path to client private key. |

If `enabled` is `false` or missing, or if `amqp.tls` is not a dict, no TLS context is created.

---

## `kontiki.registration`

Used when the service registers with a Kontiki registry.

| Key | Default | Description |
|-----|---------|-------------|
| `kontiki.registration.disable` | `False` | Set to `true` to disable registration. |
| `kontiki.registration.delay` | `2` | Delay in seconds before sending the first registration. |
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

## Registry server only

The **Kontiki registry** service uses the same `kontiki.*` keys where relevant (e.g. `kontiki.amqp`, `kontiki.http`). In addition, its config supports top-level keys (not under `kontiki`) for its own features:

- **`event_tracker.ttl_minutes`** (default: `0`), **`event_tracker.ttl_hours`** (default: `24 * 7`): event retention.
- **`event_tracker.disable`** (default: `false`): disable event tracking.
- **`event_tracker.cleanup_interval_seconds`** (default: `3600`): cleanup interval.
- **`exception_tracking.*`**: analogous options for exception retention and cleanup.

See the registry example config and source if you run the registry yourself.
