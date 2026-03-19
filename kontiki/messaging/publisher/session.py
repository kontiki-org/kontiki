from kontiki.utils import get_kontiki_header_name


class EventSession:
    def __init__(self, messenger, service_name, instance_id, session_id):
        self._messenger = messenger
        self.service_name = service_name
        self.instance_id = str(instance_id)
        self.session_id = str(session_id)

    async def publish(self, event_type, obj, extra_headers=None):
        if extra_headers is None:
            extra_headers = {}

        routing_key = f"{event_type}.{self.instance_id}"
        headers = {
            get_kontiki_header_name("session_id"): self.session_id,
            **extra_headers,
        }
        await self._messenger.publish(routing_key, obj, extra_headers=headers)
