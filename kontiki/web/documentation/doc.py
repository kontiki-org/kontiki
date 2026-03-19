from aiohttp import web

from kontiki.configuration.parameter import (
    get_kontiki_parameter,
    resolve_parameter_path,
)
from kontiki.utils import log


def get_http_documentation(container, entrypoints, version=None):
    service_class = type(container.service_instance)
    error_handlers = getattr(service_class, "http_error_handlers", None) or {}

    docs = []
    for handler in entrypoints:
        if not hasattr(handler, "_http_documentation"):
            continue

        path_or_key, method, use_config = handler._http_endpoint
        path = resolve_parameter_path(container.config, path_or_key, use_config)

        doc = {
            "path": path,
            "method": method,
            "handler_name": handler.__name__,
            **getattr(handler, "_http_documentation", {}),
        }

        errors = doc.get("errors") or ()
        derived_responses = {}
        for exc_type in errors:
            if exc_type in error_handlers:
                val = error_handlers[exc_type]
                if isinstance(val, (tuple, list)) and len(val) >= 1:
                    status = int(val[0])
                    desc = (
                        val[1]
                        if len(val) >= 2 and val[1] is not None
                        else exc_type.__name__
                    )
                    derived_responses[status] = desc
        doc["responses"] = {**derived_responses, **doc.get("responses", {})}

        if doc.get("skip_documentation"):
            continue

        if version is not None and doc.get("version") != version:
            continue

        docs.append(doc)

    return docs


def _detect_api_versions(entrypoints):
    versions = set()
    for handler in entrypoints:
        if hasattr(handler, "_http_documentation"):
            doc = getattr(handler, "_http_documentation", {}) or {}
            v = doc.get("version")
            if v:
                versions.add(v)
    return versions


def _build_openapi_from_endpoints(endpoints, title, version, description):
    openapi_doc = {
        "openapi": "3.0.0",
        "info": {"title": title, "description": description, "version": version},
        "paths": {},
        "tags": [],
    }

    all_tags = set()
    all_defs = {}

    def _collect_defs_from_schema(schema):
        if isinstance(schema, dict):
            cleaned_schema = dict(schema)
            if "$defs" in cleaned_schema:
                defs = cleaned_schema.get("$defs") or {}
                if isinstance(defs, dict):
                    all_defs.update(defs)
                cleaned_schema.pop("$defs", None)
            for key, value in list(cleaned_schema.items()):
                if isinstance(value, (dict, list)):
                    cleaned_schema[key] = _collect_defs_from_schema(value)
                elif (
                    key == "$ref"
                    and isinstance(value, str)
                    and value.startswith("#/$defs/")
                ):
                    def_name = value.replace("#/$defs/", "")
                    cleaned_schema[key] = f"#/components/schemas/{def_name}"
            return cleaned_schema
        if isinstance(schema, list):
            return [_collect_defs_from_schema(item) for item in schema]
        return schema

    for endpoint in endpoints:
        if not isinstance(endpoint, dict):
            continue

        path = endpoint.get("path")
        method = str(endpoint.get("method", "get")).lower()
        if not path or not method:
            continue

        if path not in openapi_doc["paths"]:
            openapi_doc["paths"][path] = {}

        operation = {
            "summary": endpoint.get("summary") or f"{method.upper()} {path}",
            "description": endpoint.get("description", ""),
            "tags": endpoint.get("tags", []) or [],
            "responses": {},
        }

        responses = endpoint.get("responses") or {}
        success_status = str(endpoint.get("status_code", 200))
        if success_status not in responses:
            operation["responses"][success_status] = {
                "description": "Successful response"
            }

        request_schema = endpoint.get("request_schema")
        if request_schema and method in ["post", "put", "patch"]:
            cleaned_request_schema = _collect_defs_from_schema(request_schema)
            operation["requestBody"] = {
                "content": {"application/json": {"schema": cleaned_request_schema}},
                "required": True,
            }

        response_schema = endpoint.get("response_schema")
        if response_schema:
            cleaned_response_schema = _collect_defs_from_schema(response_schema)
            status_code = str(endpoint.get("status_code", 200))
            operation["responses"].setdefault(
                status_code, {"description": "Successful response"}
            )
            operation["responses"][status_code]["content"] = {
                "application/json": {"schema": cleaned_response_schema}
            }

        for sc, resp in responses.items():
            sc_str = str(sc)
            if isinstance(resp, str):
                operation["responses"][sc_str] = {"description": resp}
            elif isinstance(resp, dict):
                operation["responses"][sc_str] = resp

        openapi_doc["paths"][path][method] = operation
        all_tags.update(operation["tags"])

    openapi_doc["tags"] = [{"name": tag} for tag in sorted(all_tags)]
    if all_defs:
        openapi_doc["components"] = {"schemas": all_defs}

    return openapi_doc


def register_auto_docs_endpoints(app, container, entrypoints, openapi_cache):
    enable = get_kontiki_parameter(container.config, "http.documentation.enabled", True)
    if not enable:
        log.info("Auto docs endpoints disabled by configuration.")
        return

    path_template = get_kontiki_parameter(
        container.config,
        "http.documentation.path_template",
        "/api/{version}/docs",
    )

    versions = _detect_api_versions(entrypoints)
    for version in versions:
        _register_docs_endpoint(
            app=app,
            container=container,
            entrypoints=entrypoints,
            openapi_cache=openapi_cache,
            version=version,
            path_template=path_template,
        )


def _register_docs_endpoint(
    app, container, entrypoints, openapi_cache, version, path_template
):
    path = path_template.format(version=version)

    if path.endswith("/docs"):
        openapi_path = path[:-5] + "/openapi.json"
    else:
        openapi_path = f"{path}.json"

    doc_title = get_kontiki_parameter(
        container.config,
        "http.documentation.title",
        container.service_name,
    )
    doc_desc = get_kontiki_parameter(
        container.config,
        "http.documentation.description",
        f"API documentation for {container.service_name}",
    )

    async def openapi_handler(request):
        cached = openapi_cache.get(version)
        if cached is not None:
            return web.json_response(cached)

        endpoints = get_http_documentation(container, entrypoints, version=version)
        openapi = _build_openapi_from_endpoints(
            endpoints=endpoints,
            title=str(doc_title),
            version=str(version),
            description=str(doc_desc),
        )
        openapi_cache[version] = openapi
        return web.json_response(openapi)

    async def docs_handler(request):
        default_ui = "swagger"
        target = f"{path}/{default_ui}"
        raise web.HTTPFound(location=target)

    try:
        app.router.add_route("GET", path, docs_handler)
        app.router.add_route("GET", openapi_path, openapi_handler)
        log.info("Auto-registered docs endpoint: GET %s (redirect)", path)
        log.info("Auto-registered OpenAPI endpoint: GET %s", openapi_path)
    except Exception as exc:
        log.error(
            "Error registering docs/openapi endpoints %s / %s: %s",
            path,
            openapi_path,
            exc,
        )

    swagger_path = f"{path}/swagger"

    async def swagger_handler(request):
        spec_url = openapi_path
        from .swagger import build_swagger_ui_html

        html = build_swagger_ui_html(
            title=f"{doc_title} ({version})",
            spec_url=spec_url,
            description=doc_desc,
        )
        return web.Response(text=html, content_type="text/html")

    try:
        app.router.add_route("GET", swagger_path, swagger_handler)
        log.info("Auto-registered Swagger UI endpoint: GET %s", swagger_path)
    except Exception as exc:
        log.error("Error registering Swagger UI endpoint %s: %s", swagger_path, exc)
