import asyncio

from kontiki.messaging import Messenger


async def main():
    amqp_url = "amqp://guest:guest@localhost"
    async with Messenger(amqp_url=amqp_url, standalone=True) as messenger:
        print("Opening session with SessionService...")
        session = await messenger.open_session("SessionService")
        print(
            f"Session opened: service={session.service_name}, "
            f"session_id={session.session_id}"
        )

        # Same session, many publishes: with 2 SessionService terminals, all
        # events must land on one pane. Split across panes = shared-queue bug.
        n = 20
        print(f"Publishing session_event {n} times within the same session...")
        for i in range(n):
            await session.publish(
                "session_event", {"message": "Hello from session", "n": i}
            )
            await asyncio.sleep(0.2)
        print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
