import inspect

from aiohttp import web

from kontiki.configuration.parameter import (
    get_kontiki_parameter,
    resolve_parameter_path,
)
from kontiki.messaging.flow import flow_id_header_name
from kontiki.runtime.handler_scope import (
    current_flow_id,
    enter_handler_scope,
    registry_exception_context,
    reset_handler_scope,
)
from kontiki.utils import log
from kontiki.web.documentation import (
    get_http_documentation,
    register_auto_docs_endpoints,
)
from kontiki.web.utils import extract_schema, parse_with_model

# -----------------------------------------------------------------------------


def prepare_http_response(response, flow_id):
    if flow_id is not None:
        response.headers[flow_id_header_name()] = flow_id
    return response


# -----------------------------------------------------------------------------


def http(
    path_or_key,
    method,
    use_config=False,
    version=None,
    summary=None,
    description=None,
    tags=None,
    request_model=None,
    response_model=None,
    status_code=200,
    responses=None,
    errors=None,
    skip_documentation=False,
    validate_request=False,
):
    def decorator(handler):
        handler._http_endpoint = (path_or_key, method, use_config)
        request_schema = None
        response_schema = None

        if request_model and inspect.isclass(request_model):
            request_schema = extract_schema(request_model)
        elif isinstance(request_model, dict):
            request_schema = request_model

        if response_model and inspect.isclass(response_model):
            response_schema = extract_schema(response_model)
        elif isinstance(response_model, dict):
            response_schema = response_model

        handler._http_documentation = {
            "version": version,
            "summary": summary,
            "description": description,
            "tags": tags or [],
            "request_model": request_model,
            "request_schema": request_schema,
            "response_model": response_model,
            "response_schema": response_schema,
            "status_code": status_code,
            "responses": responses or {},
            "errors": tuple(errors) if errors else (),
            "skip_documentation": skip_documentation,
            "validate_request": validate_request,
        }

        return handler

    return decorator


# -----------------------------------------------------------------------------


class HttpServer:
    def __init__(self, container, entrypoints):
        self.app = web.Application()
        self.entrypoints = entrypoints
        self.container = container
        self._openapi_cache = {}
        self._docs_registered = False
        self.add_entrypoints(entrypoints)

    async def setup(self):
        if not self._docs_registered:
            try:
                register_auto_docs_endpoints(
                    app=self.app,
                    container=self.container,
                    entrypoints=self.entrypoints,
                    openapi_cache=self._openapi_cache,
                )
                self._docs_registered = True
            except Exception as e:
                log.error("Error registering auto documentation endpoints: %s", e)

        self.runner = web.AppRunner(self.app)
        await self.runner.setup()

    async def start(self):
        address = get_kontiki_parameter(
            self.container.config, "http.address", "0.0.0.0"
        )
        port = get_kontiki_parameter(self.container.config, "http.port", 8080)
        self.site = web.TCPSite(self.runner, address, port)
        await self.site.start()
        log.info("Service running on http://%s:%s", address, port)

    async def stop_accepting(self):
        if self.site:
            await self.site.stop()
            self.site = None

    async def drain(self):
        if self.runner:
            await self.runner.cleanup()
            self.runner = None

    async def stop(self):
        log.info("Stopping HTTP server...")
        try:
            await self.stop_accepting()
            await self.drain()
            log.info("HTTP server stopped.")
        except Exception as e:
            log.error("Error while stopping HTTP server: %s", e)

    def add_entrypoints(self, entrypoints):
        for handler in entrypoints:
            path_or_key, method, use_config = handler._http_endpoint
            path = resolve_parameter_path(
                self.container.config, path_or_key, use_config
            )
            log.debug(
                "Registering route: %s %s with handler %s",
                method,
                path,
                handler.__name__,
            )

            # Bind the handler to the service instance
            # pylint: disable=unnecessary-dunder-call
            bound_handler = handler.__get__(self.container.service_instance)

            # Create the handler
            route_handler = self._create_handler(bound_handler, path, method, handler)

            # Register the route
            try:
                self.app.router.add_route(method, path, route_handler)
                msg = "Route %s %s successfully registered with %s"
                log.info(msg, method, path, handler.__name__)
            except Exception as e:
                log.error("Error registering route %s %s: %s", method, path, e)

    def _create_handler(self, bound_handler, path, method, original_handler):
        service_class = type(self.container.service_instance)
        error_handlers = getattr(service_class, "http_error_handlers", None) or {}

        async def handler(request, *args, **kwargs):
            msg = "Handling %s %s with params: %s"
            log.debug(msg, method, path, request.match_info)
            doc = getattr(original_handler, "_http_documentation", {}) or {}
            validate_request = bool(doc.get("validate_request"))
            request_model = doc.get("request_model")
            parsed_body = None
            operation = f"{method.upper()} {path}"
            scope = enter_handler_scope("http", operation)

            try:
                try:
                    if (
                        validate_request
                        and request_model
                        and method.upper() in ("POST", "PUT", "PATCH")
                    ):
                        if inspect.isclass(request_model):
                            try:
                                data = await request.json()
                                parsed_body = parse_with_model(request_model, data)
                            except Exception as e:
                                log.warning("Invalid request body: %s", e)
                                raise web.HTTPUnprocessableEntity(
                                    reason="Invalid request body"
                                )
                        elif isinstance(request_model, dict):
                            # No validation required for dict-based models
                            parsed_body = await request.json()

                    call_kwargs = dict(request.match_info)
                    if parsed_body is not None:
                        call_kwargs["body"] = parsed_body

                    response = await bound_handler(request, **call_kwargs)
                    if isinstance(response, web.StreamResponse):
                        return prepare_http_response(response, current_flow_id())

                    if isinstance(response, (dict, list)):
                        response = web.json_response(
                            response, status=doc.get("status_code", 200)
                        )
                        return prepare_http_response(response, current_flow_id())

                    if response is not None:
                        return prepare_http_response(response, current_flow_id())
                    return response
                except Exception as e:
                    flow_id = current_flow_id()
                    mapped = self._resolve_http_error_mapping(type(e), error_handlers)
                    if mapped is not None:
                        status, message_override = mapped
                        body = (
                            message_override
                            if message_override is not None
                            else getattr(e, "message", None) or str(e)
                        )
                        log.warning(
                            "Mapped exception in handler for %s %s: %s",
                            method,
                            path,
                            e,
                        )
                        return prepare_http_response(
                            web.json_response({"message": body}, status=status),
                            flow_id,
                        )

                    if isinstance(e, web.HTTPException):
                        prepare_http_response(e, flow_id)
                        raise

                    log.error("Error in handler for %s %s: %s", method, path, e)
                    await self.container.report_uncaught_exception(
                        e,
                        registry_exception_context(),
                    )
                    error = web.HTTPInternalServerError(reason="Internal Server Error")
                    prepare_http_response(error, flow_id)
                    raise error from e
            finally:
                reset_handler_scope(scope)

        return handler

    @staticmethod
    def _resolve_http_error_mapping(exception_type, handlers_map):
        if not handlers_map:
            return None
        for cls in inspect.getmro(exception_type):
            if cls in handlers_map:
                val = handlers_map[cls]
                if isinstance(val, (tuple, list)) and len(val) >= 2:
                    return (int(val[0]), val[1])
                if isinstance(val, (tuple, list)) and len(val) == 1:
                    return (int(val[0]), None)
                return None
        return None

    def get_documentation(self, version=None):
        return get_http_documentation(self.container, self.entrypoints, version=version)
