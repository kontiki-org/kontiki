import logging

from kontiki.configuration import get_parameter
from kontiki.delegate import ServiceDelegate
from kontiki.messaging import on_event, rpc, rpc_error


class RpcServiceDelegate(ServiceDelegate):
    async def setup(self):
        logging.info("Load config parameters in setup method")

    async def start(self):
        logging.info("You can add specific logic when starting the service")
        logging.info("Not necessary to implement this method though")

    async def stop(self):
        logging.info("You can add specific logic when stopping the service")
        logging.info("Not necessary to implement this method though")

    async def rpc_example(self, feature):
        if feature == "standard_case":
            return "Standard case"
        elif feature == "user_input_error":
            return rpc_error("USER_INPUT_ERROR", "User input error")
        elif feature == "server_error":
            raise RuntimeError("Unexpected Server error")


class RpcService:
    name = "RpcService"
    delegate = RpcServiceDelegate()

    @rpc
    async def rpc_example(self, feature):
        logging.info("Use delegate to implement business logic.")
        logging.info("Keep the service class clean and focused on the service .")
        return await self.delegate.rpc_example(feature)

    @rpc(include_headers=True)
    async def rpc_with_headers(self, _headers):
        return _headers["user_header"]

    @rpc
    async def rpc_may_fail(self, should_fail: bool):
        """Example that returns a client error when should_fail is True."""
        logging.info("rpc_may_fail called with should_fail=%s", should_fail)
        if should_fail:
            return rpc_error("SHOULD_FAIL", "The caller requested a failure.")
        return "All good"

    @rpc
    async def rpc_unhandled_exception(self):
        """Example that triggers an unhandled server-side exception."""
        logging.info("rpc_unhandled_exception called, about to raise.")
        raise RuntimeError("Unhandled error in rpc_unhandled_exception")
