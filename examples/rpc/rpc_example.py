import asyncio

from kontiki.messaging import Messenger, RpcClientError, RpcProxy, RpcServerError


class RpcServiceProxy(RpcProxy):
    def __init__(self, messenger):
        super().__init__(messenger, service_name="RpcService")


async def main():
    amqp_url = "amqp://guest:guest@localhost"
    async with Messenger(amqp_url=amqp_url, standalone=True) as messenger:
        print("Testing RPC endpoints...")
        for feature in ["standard_case", "user_input_error", "server_error"]:
            try:
                result = await RpcServiceProxy(messenger).rpc_example(feature)
                print("Result: %s" % result)
            except RpcClientError as e:
                print(
                    "Client error detected: Do what you want regarding the error code %s"
                    % e.code
                )
            except RpcServerError as e:
                print(
                    "Server error detected: Do what you want regarding the error code %s"
                    % e.code
                )

        print("Testing RPC with headers...")
        result = await RpcServiceProxy(messenger).rpc_with_headers(
            extra_headers={"user_header": "my_user_header"}
        )
        print("Result: %s" % result)

        print("Testing RPC may fail...")
        try:
            _ = await RpcServiceProxy(messenger).rpc_may_fail(should_fail=True)
        except RpcClientError as e:
            print(
                "Client error detected: Do what you want regarding the error code %s"
                % e.code
            )

        print("Testing RPC unhandled exception...")
        try:
            _ = await RpcServiceProxy(messenger).rpc_unhandled_exception()
        except RpcServerError as e:
            print(
                "Server error detected: Do what you want regarding the error code %s"
                % e.code
            )


if __name__ == "__main__":
    asyncio.run(main())
