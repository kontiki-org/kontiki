import json

from behave import then, when


@when("I publish the {event_type} event with the following payload")
def step_publish_event(context, event_type):
    payload_str = context.text.strip() if context.text else ""
    payload = json.loads(payload_str) if payload_str else None
    context.runner.publish(event_type, payload)


@then("the mock should receive the processed payload")
def step_receive_processed_payload(context):
    expected_str = context.text.strip() if context.text else ""
    expected = json.loads(expected_str) if expected_str else None

    events = context.manager.get_events(
        "TestMockService", wait_for_events=1, timeout=65
    )
    assert events, "No processed event received."
    assert events[0] == expected
    context.manager.clean_events("TestMockService")
