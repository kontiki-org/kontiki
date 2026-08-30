import json
from urllib import error, request

from behave import then, when

from kontiki.messaging.flow import FLOW_ID_LENGTH

BASE_URL = "http://127.0.0.1:8080"


def _resolve_url(path_or_url):
    if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
        return path_or_url
    return f"{BASE_URL}{path_or_url}"


def _parse_response_body(body):
    if not body:
        return None
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return body


def _response_headers(response):
    return {name.lower(): value for name, value in response.headers.items()}


def _store_http_response(context, response):
    body = response.read().decode("utf-8")
    context.http_status = response.status
    context.http_body = _parse_response_body(body)
    context.http_headers = _response_headers(response)


def _perform_request(context, req):
    try:
        with request.urlopen(req, timeout=10) as response:
            _store_http_response(context, response)
    except error.HTTPError as exc:
        _store_http_response(context, exc)


@when('I send an HTTP GET request to "{path}"')
def step_send_http_get(context, path):
    req = request.Request(_resolve_url(path), method="GET")
    _perform_request(context, req)


@when('I send an HTTP POST request to "{path}" with the following payload')
def step_send_http_post(context, path):
    payload_str = context.text.strip() if context.text else ""
    payload = payload_str.encode("utf-8")
    req = request.Request(
        _resolve_url(path),
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    _perform_request(context, req)


@then("the HTTP response status should be {status_code:d}")
def step_check_http_status(context, status_code):
    assert (
        context.http_status == status_code
    ), f"Expected HTTP status {status_code}, got {context.http_status}."


@then("the HTTP response body should be")
def step_check_http_body(context):
    expected = json.loads(context.text.strip()) if context.text else None
    assert context.http_body == expected, (
        f"Expected body:\n{json.dumps(expected, indent=2, ensure_ascii=True)}\n"
        f"Actual body:\n{json.dumps(context.http_body, indent=2, ensure_ascii=True)}"
    )


@then('the HTTP response body should contain "{content}"')
def step_check_http_body_contains(context, content):
    body = (
        context.http_body
        if isinstance(context.http_body, str)
        else json.dumps(context.http_body, ensure_ascii=True)
    )
    assert content in body, f'Expected "{content}" in HTTP response body: {body}'


@then('the HTTP response header "{header_name}" is a 12-character hex flow id')
def step_check_http_header_flow_id(context, header_name):
    headers = context.http_headers
    value = headers.get(header_name.lower())
    assert value, (
        f'Expected HTTP response header "{header_name}", ' f"got headers: {headers}"
    )
    assert len(value) == FLOW_ID_LENGTH, (
        f'Expected header "{header_name}" to be {FLOW_ID_LENGTH} characters, '
        f"got {len(value)}: {value!r}"
    )
    assert all(
        c in "0123456789abcdef" for c in value
    ), f'Expected header "{header_name}" to be lowercase hex, got {value!r}'
