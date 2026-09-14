from unittest.mock import AsyncMock, MagicMock

import pytest

from kontiki.messaging.publisher.rpc import RpcProxy


def _proxy(service_name="Svc", peer=None, instance_id=None):
    messenger = MagicMock()
    messenger.call = AsyncMock(return_value="ok")
    messenger.container = MagicMock()
    messenger.container.config = {"kontiki": {"peers": {"target": "PeerSvc"}}}
    return (
        RpcProxy(
            messenger,
            service_name=service_name,
            peer=peer,
            instance_id=instance_id,
        ),
        messenger,
    )


@pytest.mark.asyncio
async def test_proxy_without_instance_id_does_not_pin():
    proxy, messenger = _proxy()
    result = await proxy.ping(foo=1)
    assert result == "ok"
    messenger.call.assert_awaited_once_with(
        "Svc",
        "ping",
        extra_headers=None,
        flow_id=None,
        instance_id=None,
        foo=1,
    )


@pytest.mark.asyncio
async def test_proxy_pins_instance_id_on_every_method():
    proxy, messenger = _proxy(instance_id="inst-1")
    await proxy.ping(foo=1)
    messenger.call.assert_awaited_once_with(
        "Svc",
        "ping",
        extra_headers=None,
        flow_id=None,
        instance_id="inst-1",
        foo=1,
    )


@pytest.mark.asyncio
async def test_proxy_instance_id_independent_of_peer_xor():
    proxy, messenger = _proxy(service_name=None, peer="target", instance_id="inst-1")
    await proxy.ping()
    messenger.call.assert_awaited_once_with(
        "PeerSvc",
        "ping",
        extra_headers=None,
        flow_id=None,
        instance_id="inst-1",
    )


@pytest.mark.asyncio
async def test_proxy_call_instance_id_is_not_a_handler_kwarg():
    proxy, messenger = _proxy()
    await proxy.ping(instance_id="inst-1", foo=1)
    messenger.call.assert_awaited_once_with(
        "Svc",
        "ping",
        extra_headers=None,
        flow_id=None,
        instance_id="inst-1",
        foo=1,
    )


def test_proxy_empty_instance_id_raises():
    messenger = MagicMock()
    with pytest.raises(ValueError, match="instance_id"):
        RpcProxy(messenger, service_name="Svc", instance_id="")
