from unittest.mock import AsyncMock, MagicMock

import pytest

from kontiki.configuration.parameter import ConfigParameterError
from kontiki.messaging.common import KONTIKI_SESSION_OPEN_RPC
from kontiki.messaging.publisher.messenger import Messenger


def _messenger_with_container(config):
    messenger = Messenger(standalone=True)
    messenger.container = MagicMock()
    messenger.container.config = config
    messenger.call = AsyncMock(return_value=("inst-1", "sess-1"))
    return messenger


@pytest.mark.asyncio
async def test_open_session_literal_service_name():
    messenger = _messenger_with_container({})
    session = await messenger.open_session("ServiceA")
    messenger.call.assert_awaited_once_with("ServiceA", KONTIKI_SESSION_OPEN_RPC)
    assert session.service_name == "ServiceA"
    assert session.instance_id == "inst-1"
    assert session.session_id == "sess-1"


@pytest.mark.asyncio
async def test_open_session_resolves_peer():
    messenger = _messenger_with_container(
        {"kontiki": {"peers": {"target": "configured-test-service"}}}
    )
    session = await messenger.open_session(peer="target")
    messenger.call.assert_awaited_once_with(
        "configured-test-service", KONTIKI_SESSION_OPEN_RPC
    )
    assert session.service_name == "configured-test-service"


@pytest.mark.asyncio
async def test_open_session_rejects_both_service_name_and_peer():
    messenger = _messenger_with_container({})
    with pytest.raises(ValueError, match="service_name or peer, not both"):
        await messenger.open_session("ServiceA", peer="target")


@pytest.mark.asyncio
async def test_open_session_requires_service_name_or_peer():
    messenger = _messenger_with_container({})
    with pytest.raises(ValueError, match="pass service_name or peer"):
        await messenger.open_session()


@pytest.mark.asyncio
async def test_open_session_peer_requires_container():
    messenger = Messenger(standalone=True)
    messenger.container = None
    with pytest.raises(RuntimeError, match="bound to a service container"):
        await messenger.open_session(peer="target")


@pytest.mark.asyncio
async def test_open_session_peer_missing_config():
    messenger = _messenger_with_container({"kontiki": {"peers": {}}})
    with pytest.raises(ConfigParameterError):
        await messenger.open_session(peer="target")


@pytest.mark.asyncio
async def test_open_session_peer_empty_config_value():
    messenger = _messenger_with_container(
        {"kontiki": {"peers": {"target": ""}}}
    )
    with pytest.raises(ValueError, match="kontiki.peers.target"):
        await messenger.open_session(peer="target")
