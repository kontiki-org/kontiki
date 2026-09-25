import logging

from examples.events.serialization.common import ObjectToSerialize
from kontiki.messaging import on_event
from kontiki.messaging.consumer.rpc import rpc


class SerializationService:
    name = "SerializationService"

    @on_event("show_serialization")
    async def show_serialization(self, obj: ObjectToSerialize):
        logging.info(
            "@on_event received serialize_object with json (default): name=%s, age=%s",
            obj.name,
            obj.age,
        )

    @rpc
    async def show_serialization_rpc(self, obj: ObjectToSerialize):
        logging.info(
            "@rpc received serialize_object with json (default): name=%s, age=%s",
            obj.name,
            obj.age,
        )

        obj.age = 67
        return obj
