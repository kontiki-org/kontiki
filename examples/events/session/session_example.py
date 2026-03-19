import asyncio

from kontiki.messaging import Messenger


async def main():
    amqp_url = "amqp://guest:guest@localhost"
    async with Messenger(amqp_url=amqp_url, standalone=True) as messenger:
        print("Opening session with SessionService...")
        session = await messenger.open_session("SessionService")
        print(
            f"Session opened: service={session.service_name}, session_id={session.session_id}"
        )

        print("Publishing session_event within the session...")
        await session.publish("session_event", {"message": "Hello from session"})
        print("session_event published.")


if __name__ == "__main__":
    asyncio.run(main())
