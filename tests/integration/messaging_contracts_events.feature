Feature: Messaging contracts — event payload validation

    Typed @on_event payloads are validated with TypeAdapter before the
    handler runs. An invalid payload is dropped immediately: no handler
    side effect, no retry, no failed-queue retention.

    Rules locked by these scenarios:
    - A payload hint present → TypeAdapter.validate_python on the payload.
    - Validation failure → ack and drop (handler not invoked).
    - Competing failed queue is not used for schema failures.
    - Valid payload → handler runs as today.
    - Untyped event handlers are unchanged.

    Background:
        Given the test service is running

    # ------------------------------------------------------------
    # Valid typed payload
    # ------------------------------------------------------------
    @single_instance
    Scenario: Valid typed event payload is handled
        When I publish the typed_job_event event with the following payload
            """
            {
                "name": "alpha"
            }
            """
        Then the mock TestMockService should receive 1 event
            """
            [
                {
                    "name": "alpha"
                }
            ]
            """

    # ------------------------------------------------------------
    # Invalid typed payload — drop
    # ------------------------------------------------------------
    @single_instance
    Scenario: Invalid typed event payload is dropped without invoking the handler
        When I publish the typed_job_event event with the following payload
            """
            {
            }
            """
        When I wait for 2 seconds
        Then the mock TestMockService should receive 0 events
            """
            []
            """

    @single_instance
    Scenario: Invalid typed event payload is not retained in the failed queue
        When I publish the typed_job_event event with the following payload
            """
            {
            }
            """
        When I wait for 2 seconds
        Then the typed_job_event event has no failed message

    # ------------------------------------------------------------
    # Untyped still open
    # ------------------------------------------------------------
    @single_instance
    Scenario: Untyped event still delivers a free-form payload
        When I publish the simple_event event with the following payload
            """
            {
                "message": "simple_event"
            }
            """
        Then the mock TestMockService should receive 1 event
            """
            [
                {
                    "message": "simple_event"
                }
            ]
            """
