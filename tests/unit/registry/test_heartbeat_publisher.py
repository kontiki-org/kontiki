import asyncio

import pytest

from kontiki.registry.client.heartbeat_publisher import (
    HeartbeatPublisher,
    degraded_on,
    normalize_degraded_result,
)
from kontiki.registry.events import status_changed_payload


class DummyService:
    def __init__(self):
        self._degraded_flag = False
        self._reason = None

    @degraded_on
    def is_degraded(self):
        if not self._degraded_flag:
            return False
        if self._reason is not None:
            return True, self._reason
        return True


class DummyServiceRegistryClient:
    def __init__(self):
        self.calls = []

    async def heartbeat(self, degraded, reason=None):
        self.calls.append((degraded, reason))


class DummyContainer:
    def __init__(self, service_instance):
        self.service_instance = service_instance
        self.config = {}


def test_normalize_degraded_result_bool():
    assert normalize_degraded_result(False) == (False, None)
    assert normalize_degraded_result(True) == (True, None)


def test_normalize_degraded_result_tuple():
    assert normalize_degraded_result((False, "ignored")) == (False, None)
    assert normalize_degraded_result((True, None)) == (True, None)
    assert normalize_degraded_result((True, "disk full")) == (True, "disk full")


def test_status_changed_payload_includes_reason_only_when_degraded():
    active = status_changed_payload("S", "i", "down", "active")
    assert "reason" not in active

    degraded = status_changed_payload("S", "i", "active", "degraded", reason="lag")
    assert degraded["reason"] == "lag"

    degraded_no_reason = status_changed_payload("S", "i", "active", "degraded")
    assert degraded_no_reason["reason"] is None


@pytest.mark.asyncio
async def test_degraded_on_marks_method_and_publisher_uses_it(monkeypatch):
    service = DummyService()
    client = DummyServiceRegistryClient()
    publisher = HeartbeatPublisher(client)
    publisher.container = DummyContainer(service)

    # Simule get_heartbeat_interval pour ne pas dépendre de la config
    monkeypatch.setattr(
        "kontiki.registry.client.heartbeat_publisher.get_heartbeat_interval",
        lambda config: 0,
    )

    await publisher.setup()

    # Vérifie que la méthode a bien été marquée par le décorateur
    assert getattr(service.is_degraded, "_degraded", False) is True
    # Et que HeartbeatPublisher l'a bien détectée comme stop_condition
    # (on compare la fonction sous-jacente, pas l'objet bound method)
    assert publisher.stop_condition.__func__ is service.is_degraded.__func__

    # Override _send_heartbeat pour ne faire qu'un seul tour
    async def one_shot():
        should_degrade, reason = publisher._evaluate_degraded()
        publisher._is_degraded = should_degrade
        await publisher.service_registry_client.heartbeat(
            publisher._is_degraded, reason=reason if should_degrade else None
        )

    publisher._send_heartbeat = lambda: one_shot()

    # Cas 1: non dégradé -> heartbeat(False)
    task = asyncio.create_task(publisher._send_heartbeat())
    await task
    assert client.calls[-1] == (False, None)

    # Cas 2: on passe en dégradé sans reason -> heartbeat(True, None)
    service._degraded_flag = True
    task = asyncio.create_task(publisher._send_heartbeat())
    await task
    assert client.calls[-1] == (True, None)

    # Cas 3: dégradé avec reason
    service._reason = "dependency down"
    task = asyncio.create_task(publisher._send_heartbeat())
    await task
    assert client.calls[-1] == (True, "dependency down")
