import asyncio

import pytest

from kontiki.registry.client.heartbeat_publisher import HeartbeatPublisher, degraded_on


class DummyService:
    def __init__(self):
        self._degraded_flag = False

    @degraded_on
    def is_degraded(self):
        return self._degraded_flag


class DummyServiceRegistryClient:
    def __init__(self):
        self.calls = []

    async def heartbeat(self, degraded):
        self.calls.append(degraded)


class DummyContainer:
    def __init__(self, service_instance):
        self.service_instance = service_instance
        self.config = {}


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
        should_degrade = not publisher._should_send_heartbeat()
        publisher._is_degraded = should_degrade
        await publisher.service_registry_client.heartbeat(publisher._is_degraded)

    publisher._send_heartbeat = lambda: one_shot()

    # Cas 1: non dégradé -> heartbeat(False)
    task = asyncio.create_task(publisher._send_heartbeat())
    await task
    assert client.calls[-1] is False

    # Cas 2: on passe en dégradé -> heartbeat(True)
    service._degraded_flag = True
    task = asyncio.create_task(publisher._send_heartbeat())
    await task
    assert client.calls[-1] is True
