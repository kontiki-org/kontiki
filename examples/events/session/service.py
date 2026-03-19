import logging

from kontiki.delegate import ServiceDelegate
from kontiki.messaging import on_event


class SessionServiceDelegate(ServiceDelegate):
    async def setup(self):
        logging.info("SessionServiceDelegate setup called.")

    async def start(self):
        logging.info("SessionServiceDelegate start called.")

    async def stop(self):
        logging.info("SessionServiceDelegate stop called.")

    async def handle_session_event(self, payload, _headers=None):
        logging.info("Delegate handling session event: %s", payload)
        if _headers is not None:
            logging.info("Delegate received headers: %s", _headers)
        return "session event handled"


class SessionService:
    name = "SessionService"
    delegate = SessionServiceDelegate()

    @on_event("session_event", in_session=True, include_headers=True)
    async def handle_session_event(self, payload, _headers=None):
        logging.info("Service received session_event: %s", payload)
        logging.info("Service received headers: %s", _headers)
        return await self.delegate.handle_session_event(payload, _headers=_headers)
