import asyncio

from examples.events.serialization.common import ObjectToSerialize
from kontiki.messaging import Messenger, RpcProxy


async def main():
    amqp_url = "amqp://guest:guest@localhost"
    async with Messenger(amqp_url=amqp_url, standalone=True) as messenger:
        serialization_service = RpcProxy(messenger, service_name="SerializationService")

        object_to_serialize = ObjectToSerialize(name="John", age=30)

        print("Publishing show_serialization event with json...")
        await messenger.publish("show_serialization", object_to_serialize)
        print("------------------------------------------------")
        print("Publishing show_serialization rpc with json...")
        obj = await serialization_service.show_serialization_rpc(
            object_to_serialize, response_model=ObjectToSerialize
        )
        print(
            "Received return serialize_object with json (default):"
            f" name={obj.name}, age={obj.age}"
        )


if __name__ == "__main__":
    asyncio.run(main())
