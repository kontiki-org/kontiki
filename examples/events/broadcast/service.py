import logging

from kontiki.messaging import on_event


class BroadcastService:
    name = "BroadcastService"

    @on_event("broadcast_off")
    async def handle_broadcast_off(self, payload):
        logging.info("[BroadcastService] Received broadcast_off: %s", payload)

    @on_event("broadcast_on", broadcast=True)
    async def handle_broadcast_on(self, payload):
        logging.info("[BroadcastService] Received broadcast_on: %s", payload)
