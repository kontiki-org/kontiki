import asyncio

from kontiki.messaging import Messenger


async def main():
    amqp_url = "amqp://guest:guest@localhost"
    async with Messenger(amqp_url=amqp_url, standalone=True) as messenger:
        print("Publishing broadcast_off...")
        await messenger.publish(
            "broadcast_off", {"message": "Hello from broadcast example"}
        )
        print("broadcast_off published.")

        print("Publishing broadcast_on...")
        await messenger.publish(
            "broadcast_on", {"message": "Hello from broadcast example"}
        )
        print("broadcast_on published.")


if __name__ == "__main__":
    asyncio.run(main())
