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
    def __init__(self, messenger, service_name=None):
        self.messenger = messenger
        self.service_name = service_name

    def bind(self, service_name):
        self.service_name = service_name
        return self

    def __getattr__(self, method_name):
        if self.service_name is None:
            raise AttributeError(
                f"Service name not set for {self.messenger.service_name}"
            )

        async def _call(*args, extra_headers=None, **kwargs):
            kwargs.pop("extra_headers", None)
            return await self.messenger.call(
                self.service_name,
                method_name,
                *args,
                extra_headers=extra_headers,
                **kwargs,
            )

        return _call
