import inspect

from kontiki.configuration.parameter import (
    get_kontiki_parameter,
    resolve_parameter_path,
)
from kontiki.messaging.consumer.event import normalize_event_types
from kontiki.task.task import resolve_task_cron, resolve_task_interval


def registration_entrypoints(container):
    return (
        _event_entrypoints(container)
        + _rpc_entrypoints(container)
        + _http_entrypoints(container)
        + _task_entrypoints(container)
    )


def _event_entrypoints(container):
    default_attempts = get_kontiki_parameter(container.config, "amqp.max_attempts", 3)
    entrypoints = []
    for method in container.get_endpoints("on_event"):
        data = method._on_event_endpoint
        resolved = resolve_parameter_path(
            container.config, data["event_type_or_key"], data["use_config"]
        )
        if data["broadcast"]:
            mode = "broadcast"
        elif data["target_instance"]:
            mode = "in_session"
        else:
            mode = "competing"
        for event_type in normalize_event_types(resolved):
            entry = {
                "type": "event",
                "name": event_type,
                "handler": method.__name__,
                "mode": mode,
            }
            if mode == "competing":
                attempts = data["max_attempts"]
                if attempts is None:
                    attempts = default_attempts
                entry["max_attempts"] = attempts
            entrypoints.append(entry)
    return entrypoints


def _rpc_entrypoints(container):
    entrypoints = []
    for method in container.get_endpoints("rpc"):
        entrypoints.append(
            {
                "type": "rpc",
                "name": method._rpc_endpoint["name"],
                "handler": method.__name__,
            }
        )
    return entrypoints


def _http_entrypoints(container):
    if container.http_server is None:
        return []
    entrypoints = []
    for method in container.get_endpoints("http"):
        path_or_key, http_method, use_config = method._http_endpoint
        entrypoints.append(
            {
                "type": "http",
                "method": http_method,
                "path": resolve_parameter_path(
                    container.config, path_or_key, use_config
                ),
                "handler": method.__name__,
            }
        )
    return entrypoints


def _task_entrypoints(container):
    entrypoints = []
    for name, method in inspect.getmembers(
        container.service_cls, predicate=inspect.isfunction
    ):
        if "_task_cron" in method.__dict__:
            schedule = resolve_task_cron(
                container.config, method._task_cron, method._task_use_config
            )
        elif "_task_interval" in method.__dict__:
            schedule = resolve_task_interval(container.config, method._task_interval)
        else:
            continue
        entrypoints.append(
            {
                "type": "task",
                "handler": name,
                "schedule": schedule,
            }
        )
    return entrypoints
