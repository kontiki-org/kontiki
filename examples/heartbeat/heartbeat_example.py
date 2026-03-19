import asyncio
import time

from kontiki.messaging import Messenger, RpcProxy
from kontiki.registry.client.proxy import ServiceRegistryProxy
from kontiki.registry.server.core import ServiceStatus


class HeartbeatExampleProxy(RpcProxy):
    def __init__(self, messenger):
        super().__init__(messenger, service_name="heartbeat_example")


async def main():
    amqp_url = "amqp://guest:guest@localhost"
    async with Messenger(amqp_url=amqp_url, standalone=True) as messenger:
        proxy = HeartbeatExampleProxy(messenger)
        registry_proxy = ServiceRegistryProxy(messenger)

        services = await registry_proxy.get_services(
            status=ServiceStatus.DEGRADED.value
        )
        print(f"Services in degraded state: {services}")
        print("Calling HeartbeatExampleService.set_degraded(True)...")
        await proxy.set_degraded(True)
        print("Waiting for heartbeat to be sent... (10 seconds)")
        time.sleep(10)
        services = await registry_proxy.get_services(
            status=ServiceStatus.DEGRADED.value
        )
        print(f"Services in degraded state: {services}")


if __name__ == "__main__":
    asyncio.run(main())
