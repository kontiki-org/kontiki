import asyncio

from kontiki.messaging import Messenger


async def main():
    amqp_url = "amqp://guest:guest@localhost"
    async with Messenger(amqp_url=amqp_url, standalone=True) as messenger:
        print("Publishing simple_event...")
        await messenger.publish("simple_event", {"message": "Hello from simple event"})
        print("simple_event published.")

        print("Publishing dynamic_event_name...")
        await messenger.publish(
            "dynamic_event_name", {"message": "Hello from dynamic event name"}
        )
        print("dynamic_event_name published.")

        print(
            "Publishing retry_then_reject_event (will be requeued on first error, "
            "rejected on redelivery)..."
        )
        await messenger.publish(
            "retry_then_reject_event",
            {"message": "This will be requeued first, then rejected on redelivery"},
        )
        print("retry_then_reject_event published.")


if __name__ == "__main__":
    asyncio.run(main())
