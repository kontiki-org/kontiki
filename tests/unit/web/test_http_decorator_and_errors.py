from kontiki.web import http
from kontiki.web.web import HttpServer


def test_http_decorator_sets_endpoint_and_documentation():
    @http(
        "/hello",
        "GET",
        use_config=False,
        version="v1",
        summary="Hello",
        description="Hello endpoint",
        tags=["greetings"],
        request_model={"type": "object"},
        response_model={"type": "object"},
        status_code=201,
        responses={400: "Bad request"},
        errors=[ValueError],
        skip_documentation=False,
        validate_request=True,
    )
    async def handler(request):
        return {"message": "hello"}

    # Endpoint metadata
    assert hasattr(handler, "_http_endpoint")
    path_or_key, method, use_config = handler._http_endpoint
    assert path_or_key == "/hello"
    assert method == "GET"
    assert use_config is False

    # Documentation metadata
    assert hasattr(handler, "_http_documentation")
    doc = handler._http_documentation
    assert doc["version"] == "v1"
    assert doc["summary"] == "Hello"
    assert doc["description"] == "Hello endpoint"
    assert doc["tags"] == ["greetings"]
    assert doc["request_model"] == {"type": "object"}
    assert doc["response_model"] == {"type": "object"}
    assert doc["status_code"] == 201
    assert doc["responses"] == {400: "Bad request"}
    assert doc["errors"] == (ValueError,)
    assert doc["skip_documentation"] is False
    assert doc["validate_request"] is True


def test_resolve_http_error_mapping_with_exact_match():
    class BaseError(Exception):
        pass

    class SpecificError(BaseError):
        pass

    handlers_map = {
        BaseError: (400, "base"),
        SpecificError: (422, "specific"),
    }

    result = HttpServer._resolve_http_error_mapping(SpecificError, handlers_map)
    assert result == (422, "specific")


def test_resolve_http_error_mapping_with_base_class_fallback():
    class BaseError(Exception):
        pass

    class SpecificError(BaseError):
        pass

    handlers_map = {
        BaseError: (400, "base"),
    }

    result = HttpServer._resolve_http_error_mapping(SpecificError, handlers_map)
    assert result == (400, "base")


def test_resolve_http_error_mapping_single_element_tuple():
    class CustomError(Exception):
        pass

    handlers_map = {
        CustomError: (418,),  # Only status code
    }

    result = HttpServer._resolve_http_error_mapping(CustomError, handlers_map)
    assert result == (418, None)


def test_resolve_http_error_mapping_no_match():
    class CustomError(Exception):
        pass

    handlers_map = {}
    result = HttpServer._resolve_http_error_mapping(CustomError, handlers_map)
    assert result is None
