from kontiki.configuration.parameter import get_kontiki_parameter


class RpcError(Exception):
    def __init__(self, method_name, code, message):
        self.method_name = method_name
        self.code = code
        self.message = message
        super().__init__(f"{self.method_name} [{self.code}]: {self.message}")


class RpcTimeoutError(RpcError):
    def __init__(self, method_name):
        super().__init__(method_name, "RPC_TIMEOUT", "The RPC method timed out.")


class RpcClientError(RpcError):
    pass


class RpcServerError(RpcError):
    pass


class RpcProxy:
    def __init__(self, messenger, service_name=None, *, peer=None):
        if service_name is not None and peer is not None:
            raise ValueError("RpcProxy(): pass service_name or peer, not both")
        if peer is not None and (not isinstance(peer, str) or not peer):
            raise ValueError(
                f"RpcProxy(): peer must be a non-empty string, got {peer!r}"
            )
        self.messenger = messenger
        self._peer = peer
        self.service_name = service_name

    def bind(self, service_name):
        self._peer = None
        self.service_name = service_name
        return self

    def resolve_service_name(self):
        if self._peer is None:
            return self.service_name
        if self.service_name is not None:
            return self.service_name
        container = self.messenger.container
        if container is None:
            raise RuntimeError(
                f"RpcProxy(peer={self._peer!r}) requires a messenger "
                "bound to a service container"
            )
        resolved = get_kontiki_parameter(container.config, f"peers.{self._peer}")
        if not isinstance(resolved, str) or not resolved:
            raise ValueError(
                f"kontiki.peers.{self._peer} must be a non-empty string, "
                f"got {resolved!r}"
            )
        self.service_name = resolved
        return resolved

    def __getattr__(self, method_name):
        service_name = self.resolve_service_name()
        if service_name is None:
            raise AttributeError(
                f"Service name not set for {self.messenger.service_name}"
            )

        async def _call(*args, extra_headers=None, flow_id=None, **kwargs):
            kwargs.pop("extra_headers", None)
            kwargs.pop("flow_id", None)
            return await self.messenger.call(
                service_name,
                method_name,
                *args,
                extra_headers=extra_headers,
                flow_id=flow_id,
                **kwargs,
            )

        return _call
