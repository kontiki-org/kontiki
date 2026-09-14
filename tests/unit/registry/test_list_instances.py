from datetime import datetime, timezone
from unittest.mock import MagicMock

from kontiki.registry.server.core import ServiceRegistryCore


def _core():
    core = ServiceRegistryCore()
    core.container = MagicMock()
    core.container.service_name = "ServiceRegistry"
    return core


def _register(core, service_name, instance_id, heartbeat_interval=10):
    if service_name not in core.registry.services:
        core.registry.services[service_name] = {}
    core.registry.services[service_name][instance_id] = {
        "heartbeat_interval": heartbeat_interval
    }


def test_list_instances_sorted_live_ids():
    core = _core()
    _register(core, "Worker", "b-id")
    _register(core, "Worker", "a-id")
    now = datetime.now(timezone.utc)
    core.heartbeat_manager.heartbeats[("Worker", "b-id")] = now
    core.heartbeat_manager.heartbeats[("Worker", "a-id")] = now

    assert core.list_instances("Worker") == ["a-id", "b-id"]


def test_list_instances_includes_degraded_omits_down():
    core = _core()
    _register(core, "Worker", "live")
    _register(core, "Worker", "degraded")
    _register(core, "Worker", "down")
    now = datetime.now(timezone.utc)
    core.heartbeat_manager.heartbeats[("Worker", "live")] = now
    core.heartbeat_manager.heartbeats[("Worker", "degraded")] = now
    core.heartbeat_manager.degraded_services.append(("Worker", "degraded"))

    assert core.list_instances("Worker") == ["degraded", "live"]


def test_list_instances_unknown_or_blank_is_empty():
    core = _core()
    assert core.list_instances("Unknown") == []
    assert core.list_instances("") == []
    assert core.list_instances("  ") == []


def test_list_instances_does_not_special_case_registry_name():
    core = _core()
    assert core.list_instances("ServiceRegistry") == []
    assert core.is_live("ServiceRegistry") is True
