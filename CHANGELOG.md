# Changelog

## [1.16.0] - 2026-09-19

- Each `publish` / `call` stamps `kontiki_hop_id` (new id per emission),
  `kontiki_parent_hop_id` (inbound hop; omitted for `@http` / `@task` /
  outbound outside a handler), `kontiki_entrypoint`, `kontiki_operation`,
  and `kontiki_rpc_service` on `call` only.
- Exception records include `hop_id` (inbound hop; `null` for HTTP/task)
  and `exception_id`.

## [1.15.0] - 2026-09-18

- Exception records are a flat ops index: `entrypoint`, `operation`, and
  `flow_id` from the handler scope. `publish_exception` takes only the
  exception (no `context` bag). Uncaught handlers log with `exc_info`.
  `registry.exception.recorded` stays on the bus and is not stored in
  `get_events`. Mapped HTTP, `HTTPException`, and returned `rpc_error`
  are not recorded.

## [1.14.0] - 2026-09-16

- Registration `config` is the top-level `public` mapping when it is a
  non-empty dict (`get_services` metadata and `registry.instance.registered`).
  `kontiki`, `logging`, and other roots are not exported.
  `kontiki.registration.configuration.public_paths` has no effect.

## [1.13.0] - 2026-09-14

- RPC `instance_id=` on `messenger.call` and `RpcProxy` targets one process
  (`{service}.{method}.{instance_id}`). Default competing RPC is unchanged.
  Unknown or dead id → `RpcTimeoutError`.
- `Messenger.call` / testing `call`: `service_name` and `method_name` are
  positional-only so a handler may take a `service_name` kwarg (e.g. registry
  `list_instances`).
- Registry `list_instances(service_name)` and `GET /instances/{service_name}`
  return the sorted live ids (`active` / `degraded`). Empty list for unknown
  names (HTTP 200). The registry's own name is not special-cased (unlike
  `GET /live/ServiceRegistry`).
- Queues keyed by `instance_id` (targeted RPC, `broadcast`, `in_session`) are
  `exclusive` + `auto_delete`. Shared competing queues stay durable.

## [1.12.0] - 2026-09-12

- Messenger `publish` / `call` raise `AmqpDisconnectedError` (from
  `kontiki.messaging`) when AMQP is not connected, including during
  `reconnect()` and when `amqp.required: false`. Callers that caught
  `RuntimeError` on disconnect must catch `AmqpDisconnectedError`.
- Registry client publish (register, heartbeat, exception, unregister) logs at
  `debug` instead of `info`.
- Default log format pads `flow_id` to 19 (`%(flow_id)-19s`), matching
  `[flow=` + 12 hex + `]`.

## [1.11.1] - 2026-09-12

- `@rpc` / `@on_event` get a `flow_id` at handler entry (reuse inbound
  `kontiki_flow_id` when present, otherwise generate), same as `@http` / `@task`.
  `[no flow]` remains only for logs outside a handler.
- Default log format: `levelname` is unpadded (`INFO` vs `ERROR` / `DEBUG`
  shifts the rest of the line). `flow_id` stays padded.

## [1.11.0] - 2026-09-09

- `@task(cron="…")`: 5-field crontab in the process local timezone, complementary
  to `@task(interval=…)`. Default `immediate=False`. Config:
  `@task(cron="app.backup.schedule", use_config=True)`. Late ticks still run; no
  catch-up. Example: `examples/task/` (`make run-task-service`).
- `kontiki.amqp.required` (default `true`): fail-fast at start if the broker is
  unreachable. `false`: `@http` / `@task` start even when RabbitMQ is down (work
  that does not need the bus, e.g. a database dump); registry, heartbeats, and
  exception reporting connect when it is up. `publish` / `call` raise while
  disconnected. Distinct from `registration.disable`. Integration suite
  `@amqp_required`.
- `kontiki.registration.group` is a free-form TUI filter (not a closed set).
  Exception reporting is the same for every group.
- Docs: one-stack positioning (business, ops, monitoring); logging reference
  aligned with injected filters / default formatter / `logging.directory`.
  Examples (`examples/common.yaml`) use console `StreamHandler` and inherit the
  default formatter.

## [1.10.0] - 2026-09-05

- Registry registration includes `kontiki_version` (framework version at
  `register()`), distinct from `service_version`. Exposed in `get_services`
  metadata and `registry.instance.registered`.

## [1.9.0] - 2026-09-04

- Registry `get_services` (RPC and `GET /services`) includes `last_heartbeat`
  (ISO-8601 UTC of the last heartbeat received, or `null`) and `degraded_reason`
  (last non-empty reason while the instance is degraded, otherwise `null`).

## [1.8.1] - 2026-09-03

- Default log format: `short_instance_id` only (no `service_name` in the line),
  with padded columns for lnav —
  `%(asctime)s - %(short_instance_id)s - %(levelname)-8s - %(flow_id)-20s - %(message)s`.
  Service name stays in the log filename; `service_name` / `short_instance_id`
  remain on records for custom formatters.

## [1.8.0] - 2026-09-03

- Logging file naming (opt-in): set `logging.directory` to have Kontiki impose
  `{directory}/{service_name}-{short_instance_id}.log` on every `FileHandler`
  subclass (replicas-safe, KontikiTUI / lnav friendly). Without `directory`,
  explicit `filename` remains valid (legacy).
- Logging defaults when omitted from YAML: `version`, `disable_existing_loggers`,
  default formatter, and a propagating `kontiki` logger so framework logs stay
  visible. Service identity filter on all handlers (`service_name` /
  `short_instance_id` available to custom formatters).
- Documents the recommended mode in `docs/advanced-features.md`; example and
  reference in `docs/kontiki-config.example.yaml` and `docs/configuration.md`.
  Integration suite `@logging`.

## [1.7.1] - 2026-09-02

- Fixes `@on_event(..., in_session=True)` queue topology: each instance declares `{service}.{event}.{instance_id}.queue` (same naming pattern as `broadcast`) so session-targeted events are not competed for by other replicas.
- Fixes registry `register_again` signal: each instance declares `{service}.{instance_id}.register_again.queue` instead of a shared `register_again.queue` for the whole vhost.
- Session example publishes repeatedly on one session so multi-instance pinning can be checked with two `run-session-service` terminals.

## [1.7.0] - 2026-08-29

- Graceful shutdown: three-phase `ServiceContainer.stop()` (stop accepting → drain in-flight work → force close). Configurable via `kontiki.shutdown.grace_seconds` (default 25). HTTP, AMQP consumers, `@task`, registry unregister/heartbeat follow the shutdown spec.
- Handler scope: unified execution context on `@http`, `@rpc`, `@on_event`, and `@task` (single ContextVar for `flow_id`, `kind`, and `operation`). `@http` and `@task` generate a `flow_id` at handler entry; `@http` responses include header `kontiki_flow_id`. Uncaught exceptions in `@on_event` handlers are reported to the registry when `kontiki.registration.report_uncaught_exceptions` is enabled (same path as RPC / HTTP / task).
- Logs a deprecation warning when `kontiki.amqp.serialization` is `json`; `pickle` remains the supported AMQP format.

## [1.6.2] - 2026-08-29

- Fixes Messenger RPC callback handling: acknowledge every reply (including unknown / post-timeout correlation ids), consume the callback queue once at setup, retry `call()` once after `ChannelInvalidStateError`, and make `reconnect()` recreate the channel and callback queue.

## [1.6.1] - 2026-08-23

- `messenger.open_session(peer="…")` resolves `kontiki.peers.<peer>` (same XOR contract as `RpcProxy`). Documented in `docs/features.md`, `docs/configuration.md`, and `docs/advanced-features.md`.

## [1.6.0] - 2026-08-22

- `@on_event` accepts a list of exact event types (literal or via `use_config=True` as string or list). One queue and bind per type; empty list fails fast at startup. Documented in `docs/features.md` and `docs/advanced-features.md`.
- `kontiki.service_name` overrides the logical service identity (RPC queues, registry). Priority: config > class `name` > class name.
- `RpcProxy(..., peer="…")` resolves `kontiki.peers.<peer>` (preferred for deployment-specific targets); `service_name=` remains for fixed platform identities. Documented in `docs/features.md`, `docs/configuration.md`, and `docs/advanced-features.md`.

## [1.5.0] - 2026-07-24

- Automatic flow correlation: a short `flow_id` propagates on AMQP `publish` / RPC `call` (header `kontiki_flow_id`), is restored on inbound `@on_event` / `@rpc`, and appears on log lines (`[flow=…]` / `[no flow]`). Optional `flow_id=` override; otherwise ContextVar → header → generate. Logging filter injected at boot without YAML (`current_flow_id()` helper).
- `@degraded_on` may return `(True, reason)`; on transition to `degraded`, `registry.instance.status_changed` includes optional `reason` for alerting (not stored for `get_services`).

## [1.4.0] - 2026-07-22

- Registration group: services send a first-class `group` field on registry `register` (`kontiki.registration.group`, default `business`). 
- Documents `kontiki.registration.group` in `docs/configuration.md` and the example config.
- Corrects `docs/features.md`: multi-file config merge does not override conflicting leaf values (complementary keys only; conflicts raise an error).

## [1.3.0] - 2026-07-19

- Registry HTTP live probe: `GET /live/{service_name}` returns 200 when at least one instance is `active` or `degraded`, 503 otherwise. The registry's own name returns 200 without self-registration (orchestrator-friendly for bus-only services).
- Documents the live probe in `docs/features.md`.

## [1.2.0] - 2026-07-18

- Task intervals can be a config key string resolved at service start (e.g. `@task("app.cleanup.interval")`), in addition to a literal number of seconds.
- Uncaught exceptions in RPC, unmapped HTTP, and `@task` entrypoints are reported to the registry by default (`kontiki.registration.report_uncaught_exceptions`; set to `false` to opt out). Same path as `publish_exception` / `registry.exception.recorded`.
- Invalid HTTP request bodies (Pydantic validation) now return `422 Unprocessable Entity` instead of being wrapped as `500`.
- Documents configurable task intervals and automatic exception reporting in `docs/features.md` and `docs/configuration.md`.

## [1.1.0] - 2026-07-15

- Registry server publishes lifecycle events on the standard event exchange: `registry.instance.registered`, `registry.instance.deregistered`, `registry.instance.status_changed`, `registry.exception.recorded`.
- Registry monitors instance status (`active`, `degraded`, `down`) and publishes `registry.instance.status_changed` on transitions.
- Adds integration tests for the service registry (`@registry` suite).
- Documents registry lifecycle events in `docs/features.md`.
- Fixes HTTP startup log to appear only after the server binds successfully.

## [1.0.2] - 2026-03-26

- Fixes #4 (integration tests can't import services).
- Fixes #6 (Registry cleanup timezone mismatch).
- Adds integration tests (RPC, HTTP, on_event, task).
- Improves test runtime/service management.

## [1.0.1] - 2026-03-18

Fix project metadata (GitHub URLs), update supported Python versions (3.11–3.13), and add CI matrix to test against them.

## [1.0.0] - 2026-03-11

Initial public release.
See `docs/features.md` and `docs/configuration.md` for a detailed description of the framework.
