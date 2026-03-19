import logging

from kontiki.delegate import ServiceDelegate
from kontiki.messaging import on_event


class SerializationService:
    name = "SerializationService"

    @on_event("show_serialization")
    async def show_serialization(self, object):
        logging.info(
            "Service received serialize_object with pickle (default): name=%s, age=%s",
            object.name,
            object.age,
        )
