from kontiki.messaging import rpc, rpc_error


class TestService:
    # ------------------------------------------------------------
    # RPC methods
    # ------------------------------------------------------------

    @rpc
    async def rpc_example(self, feature):
        if feature == "standard_case":
            return "Standard case"
        elif feature == "user_input_error":
            return rpc_error("USER_INPUT_ERROR", "User input error")
        elif feature == "server_error":
            raise RuntimeError("Unexpected Server error")

    @rpc(include_headers=True)
    async def rpc_with_headers(self, _headers):
        return _headers["user_header"]
