# Changelog

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
