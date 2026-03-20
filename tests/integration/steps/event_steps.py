import json

from behave import then, when


@when("I publish the {event_type} event with the following payload")
def step_publish_event(context, event_type):
    payload_str = context.text.strip() if context.text else ""
    payload = json.loads(payload_str) if payload_str else None
    context.runner.publish(event_type, payload)


@then("the mock should receive {event_count:d} event")
@then("the mock should receive {event_count:d} events")
def step_receive_processed_payloads(context, event_count):
    expected_str = context.text.strip() if context.text else ""
    expected_events = json.loads(expected_str) if expected_str else []

    events = context.manager.get_events(
        "TestMockService", wait_for_events=event_count, timeout=65
    )
    assert (
        len(events) >= event_count
    ), f"Expected {event_count} events, got {len(events)}."
    assert events[:event_count] == expected_events
    context.manager.clean_events("TestMockService")
