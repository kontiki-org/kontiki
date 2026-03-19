import logging

from kontiki.registry.common import REGISTER_RKEY, UNREGISTER_RKEY, nested_dict

# -----------------------------------------------------------------------------


class Registry:
    def __init__(self, core):
        self.core = core
        self.services = nested_dict()

    async def setup(self):
        # Declare queues
        handlers = {
            REGISTER_RKEY: self._handle_register,
            UNREGISTER_RKEY: self._handle_unregister,
        }

        for rkey, callback in handlers.items():
            await self.core.create_and_consume_queue(rkey, callback)

    async def _handle_register(self, message):
        async with message.process():
            logging.info("Received registration message: %s", message.body)
            try:
                data = self.core.serializer.loads(message.body)
                service_name = data["service_name"]
                instance_id = data["instance_id"]

                # Services registration
                self.services[service_name][instance_id] = data
                logging.info("Registering service %s#%s", service_name, instance_id)

            except Exception as e:
                logging.error("Error processing registration: %s", e)

    async def _handle_unregister(self, message):
        async with message.process():
            logging.info("Received unregistration message: %s", message.body)
            try:
                data = self.core.serializer.loads(message.body)
                service_name = data["service_name"]
                instance_id = data["instance_id"]

                if service_name not in self.services:
                    logging.error("Service %s not found.", service_name)
                    return

                if instance_id not in self.services[service_name]:
                    logging.error(
                        "Instance %s of service %s not found.",
                        instance_id,
                        service_name,
                    )
                    return

                del self.services[service_name][instance_id]

                # No more service instances, service entry removal.
                if not self.services[service_name]:
                    logging.info(
                        "No active instances for %s. Cleaning up...", service_name
                    )
                    # Service entry removal.
                    del self.services[service_name]

            except Exception as e:
                logging.error("Error processing unregistration: %s", e)

    def has_service(self, service_name):
        return service_name in self.services

    def has_service_instance(self, service_name, instance_id):
        has_service = self.has_service(service_name)
        return has_service and instance_id in self.services[service_name]
