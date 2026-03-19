import asyncio
import time

from kontiki.messaging import Messenger, RpcProxy
from kontiki.registry.client.proxy import ServiceRegistryProxy


class RegistryExampleProxy(RpcProxy):
    def __init__(self, messenger):
        super().__init__(messenger, service_name="RegistryExampleService")


async def main():
    amqp_url = "amqp://guest:guest@localhost"
    async with Messenger(amqp_url=amqp_url, standalone=True) as messenger:
        proxy = RegistryExampleProxy(messenger)
        registry_proxy = ServiceRegistryProxy(messenger)

        print("Calling RegistryExampleService.rpc_in_registry()...")
        await proxy.rpc_in_registry()

        print("Publishing event_display_in_registry...")
        await messenger.publish(
            "event_display_in_registry", {"message": "hello from client"}
        )

        print("Calling RegistryExampleService.raise_exception()...")
        await proxy.raise_exception()

        time.sleep(1)

        print("Calling ServiceRegistry.get_services()...")
        services = await registry_proxy.get_services()
        print(f"Services: {services}")

        print("Calling ServiceRegistry.get_events()...")
        events = await registry_proxy.get_events()
        print(f"Events: {events}")

        print("Calling ServiceRegistry.get_exceptions()...")
        exceptions = await registry_proxy.get_exceptions()
        print(f"Exceptions: {exceptions}")


if __name__ == "__main__":
    asyncio.run(main())
