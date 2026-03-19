from aiohttp import web

from kontiki.messaging.consumer.rpc import rpc, rpc_error
from kontiki.registry.server.core import ServiceRegistryCore, ServiceStatus
from kontiki.web.web import http

# -----------------------------------------------------------------------------


class ServiceRegistry:
    core = ServiceRegistryCore()

    # -----------------------------------------------------------------------------
    # HTTP API
    # -----------------------------------------------------------------------------
    @http("/services", "GET")
    async def http_get_all_services(self, request):
        services = self.core.get_services()
        return web.json_response(services)

    @http("/services/{status}", "GET")
    async def http_get_services_by_status(self, request, status):
        try:
            _ = ServiceStatus(status)
        except ValueError as err:
            raise web.HTTPBadRequest(reason=f"Invalid status: {status}") from err

        services = self.core.get_services(status)
        return web.json_response(services)

    @http("/events", "GET")
    async def http_get_events(self, request):
        return web.json_response(self.core.get_events())

    @http("/events/{filter_field}/{value}", "GET")
    async def http_get_filtered_events(self, request, filter_field, value):
        matching_events = [
            event
            for event in self.core.get_events()
            if event.get(filter_field) == value
        ]
        return web.json_response(matching_events)

    @http("/exceptions", "GET")
    async def http_get_exceptions(self, request):
        return web.json_response(self.core.get_exceptions())

    @http("/exceptions/{filter_field}/{value}", "GET")
    async def http_get_filtered_exceptions(self, request, filter_field, value):
        matching_exceptions = [
            exception
            for exception in self.core.get_exceptions()
            if exception.get(filter_field) == value
        ]
        return web.json_response(matching_exceptions)

    # -----------------------------------------------------------------------------
    # AMQP API
    # -----------------------------------------------------------------------------

    @rpc
    async def get_services(self, status=None):
        if status is not None:
            try:
                _ = ServiceStatus(status)
            except ValueError:
                return rpc_error("INVALID_STATUS", f"Invalid status: {status}")
        return self.core.get_services(status)

    @rpc
    async def get_events(self):
        return self.core.get_events()

    @rpc
    async def get_filtered_events(self, filter_field, value):
        matching_events = [
            event
            for event in self.core.get_events()
            if event.get(filter_field) == value
        ]
        return matching_events

    @rpc
    async def get_exceptions(self):
        return self.core.get_exceptions()

    @rpc
    async def get_filtered_exceptions(self, filter_field, value):
        matching_exceptions = [
            exception
            for exception in self.core.get_exceptions()
            if exception.get(filter_field) == value
        ]
        return matching_exceptions
