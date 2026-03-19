import logging
from datetime import datetime, timedelta

from aio_pika import Message

from kontiki.registry.common import HEARTBEAT_RKEY

# -----------------------------------------------------------------------------


class HeartbeatManager:
    def __init__(self, core):
        self.core = core
        self.heartbeats = {}
        self.degraded_services = []
        self.started_at = datetime.now()

    async def setup(self):
        # Declare queues
        await self.core.create_and_consume_queue(HEARTBEAT_RKEY, self._handle_heartbeat)

    async def _handle_heartbeat(self, message):
        async with message.process():
            logging.debug("Received heartbeat message: %s", message.body)
            try:
                data = self.core.serializer.loads(message.body)
                service_name = data["service_name"]
                instance_id = data["instance_id"]
                degraded = data["degraded"]
                await self.store_heartbeat(service_name, instance_id, degraded)

            except Exception as e:
                logging.error("Error processing heartbeat: %s", e)

    async def store_heartbeat(self, service_name, instance_id, degraded):
        logging.debug("Stored heartbeats = %s", self.heartbeats)
        try:
            service_str = f"{service_name}#{instance_id}"

            service_instance = (service_name, instance_id)
            if self.core.registry.has_service_instance(service_name, instance_id):
                if degraded and service_instance not in self.degraded_services:
                    self.degraded_services.append(service_instance)
                    logging.warning("%s enters degraded state.", service_str)
                else:
                    if not degraded:
                        if service_instance in self.degraded_services:
                            logging.info(
                                "%s recovers from degraded state.", service_str
                            )
                            self.degraded_services.remove(service_instance)
                self.heartbeats[service_instance] = datetime.now()
                logging.debug("Heartbeat updated for %s.", service_str)
            else:
                # We dont ask for registering again when we just start. We might have
                # received a heartbeat before the service registry is ready.
                grace_period = timedelta(seconds=15)
                if datetime.now() - self.started_at < grace_period:
                    logging.warning(
                        "Heartbeat for unknown service %s received during"
                        " grace period, ignoring for now.",
                        service_str,
                    )
                    return
                logging.warning(
                    "Heartbeat received for unknown service %s", service_str
                )
                registry_admin_exchange = self.core.registry_admin_exchange
                rkey = f"{service_name}.{instance_id}.register_again"
                message = Message(body=b"")
                await registry_admin_exchange.publish(message, routing_key=rkey)
                logging.info("Published register_again message to %s", rkey)

        except Exception as e:
            logging.error("Heartbeat Storage Error : %s", e)

    def get_last_heartbeat(self, service_name, instance_id):
        return self.heartbeats.get((service_name, instance_id), None)

    def is_degraded(self, service_name, instance_id):
        return (service_name, instance_id) in self.degraded_services
