import asyncio

from kontiki.messaging import Messenger, RpcProxy
from kontiki.registry.client.proxy import ServiceRegistryProxy


class RpcServiceProxy(RpcProxy):
    def __init__(self, messenger, instance_id=None):
        super().__init__(messenger, service_name="RpcService", instance_id=instance_id)


async def main():
    amqp_url = "amqp://guest:guest@localhost"
    async with Messenger(amqp_url=amqp_url, standalone=True) as messenger:
        ids = await ServiceRegistryProxy(messenger).list_instances("RpcService")
        print(f"Live RpcService instances: {ids}")

        # With 2 RpcService terminals, each whoami must match the targeted id.
        # Same reply on every call = competing shared queue, not instance pin.
        for instance_id in ids:
            result = await RpcServiceProxy(messenger, instance_id=instance_id).whoami()
            print(f"instance_id={instance_id} answered: {result}")


if __name__ == "__main__":
    asyncio.run(main())
