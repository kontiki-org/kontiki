import json

from behave import then, when


@when("I publish the {event_type} event with the following payload")
def step_publish_event(context, event_type):
    payload_str = context.text.strip() if context.text else ""
    payload = json.loads(payload_str) if payload_str else None
    context.runner.publish(event_type, payload)


@then("the mock {mock_name} should receive {event_count:d} event")
@then("the mock {mock_name} should receive {event_count:d} events")
@then("the mock {mock_name} should have received {event_count:d} events")
def step_receive_processed_payloads(context, mock_name, event_count):
    expected_str = context.text.strip() if context.text else ""
    expected_events = json.loads(expected_str) if expected_str else []

    events = context.manager.get_events(
        mock_name, wait_for_events=event_count, timeout=65
    )
    assert (
        len(events) >= event_count
    ), f"Expected {event_count} events, got {len(events)}."
    actual_events = events[:event_count]
    assert sorted(actual_events) == sorted(expected_events), (
        f"Events mismatch for mock '{mock_name}'.\n"
        f"Expected ({len(expected_events)}):\n"
        f"{json.dumps(expected_events, indent=2, ensure_ascii=True)}\n"
        f"Actual ({len(actual_events)}):\n"
        f"{json.dumps(actual_events, indent=2, ensure_ascii=True)}"
    )
    context.manager.clean_events(mock_name)
