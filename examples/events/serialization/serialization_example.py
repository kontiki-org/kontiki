import asyncio

from examples.events.serialization.common import ObjectToSerialize
from kontiki.messaging import Messenger


async def main():
    amqp_url = "amqp://guest:guest@localhost"
    async with Messenger(amqp_url=amqp_url, standalone=True) as messenger:
        object_to_serialize = ObjectToSerialize(name="John", age=30)

        print("Publishing show_serialization event with pickle (default)...")
        await messenger.publish("show_serialization", object_to_serialize)
        print("show_serialization published with pickle (default).")


if __name__ == "__main__":
    asyncio.run(main())
