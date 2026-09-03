# Changelog

## [1.8.0] - 2026-09-03

- Logging file naming (opt-in): set `logging.directory` to have Kontiki impose
  `{directory}/{service_name}-{short_instance_id}.log` on every `FileHandler`
  subclass (replicas-safe, KontikiTUI / lnav friendly). Without `directory`,
  explicit `filename` remains valid (legacy).
- Logging defaults when omitted from YAML: `version`, `disable_existing_loggers`,
  default formatter
  (`service#short` + `flow_id`), and a propagating `kontiki` logger so framework
  logs stay visible. Service identity filter on all handlers.
- Documents the recommended mode in `docs/advanced-features.md`; contract in
  `docs/kontiki-logging-filename.md`; example and reference in
  `docs/kontiki-config.example.yaml` and `docs/configuration.md`. Integration
  suite `@logging`.

## [1.7.1] - 2026-09-02

- Fixes `@on_event(..., in_session=True)` queue topology: each instance declares `{service}.{event}.{instance_id}.queue` (same naming pattern as `broadcast`) so session-targeted events are not competed for by other replicas. See `docs/fix-in-session-queue-topology.md`.
- Fixes registry `register_again` signal: each instance declares `{service}.{instance_id}.register_again.queue` instead of a shared `register_again.queue` for the whole vhost. See `docs/fix-register-again-queue-topology.md`.
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
