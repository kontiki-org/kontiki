Feature: Events

    Background:
        Given the test service is running

    # ------------------------------------------------------------
    # Simple Event
    # ------------------------------------------------------------
    @single_instance
    Scenario: simple_event is handled and processed
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

    # ------------------------------------------------------------
    # Dynamic Event Name
    # ------------------------------------------------------------
    @single_instance
    Scenario: tests.event.name is handled and processed
        When I publish the dynamic_event_name event with the following payload
            """
            {
                "message": "dynamic_event_name"
            }
            """
        Then the mock TestMockService should receive 1 event
            """
            [
                {
                    "message": "dynamic_event_name"
                }
            ]
            """

    # ------------------------------------------------------------
    # Retry Ok
    # ------------------------------------------------------------
    @single_instance
    Scenario: retry_ok is handled and processed
        When I publish the retry_ok event with the following payload
            """
            {
                "message": "retry_ok"
            }
            """
        Then the mock TestMockService should receive 1 event
            """
            [
                {
                    "message": "retry_ok"
                }
            ]
            """

    # ------------------------------------------------------------
    # Broadcast Off
    # ------------------------------------------------------------
    @multi_instance
    Scenario: broadcast_off is handled and processed
        When I publish the broadcast_off event with the following payload
            """
            {
                "message": "broadcast_off"
            }
            """
        Then the mock TestMockService should receive 1 event
            """
            [
                {
                    "message": "broadcast_off"
                }
            ]
            """

    # ------------------------------------------------------------
    # Broadcast On
    # ------------------------------------------------------------
    @multi_instance
    Scenario: broadcast_on is handled and processed
        When I publish the broadcast_on event with the following payload
            """
            {
                "message": "broadcast_on"
            }
            """
        Then the mock TestMockService should receive 2 events
            """
            [
                {
                    "message": "broadcast_on"
                },
                {
                    "message": "broadcast_on"
                }
            ]
            """

    # ------------------------------------------------------------
    # Event type list — literal
    # ------------------------------------------------------------
    @single_instance
    Scenario: multi_event_a and multi_event_b are handled by one literal list
        When I publish the multi_event_a event with the following payload
            """
            {
                "message": "multi_event_a"
            }
            """
        Then the mock TestMockService should receive 1 event
            """
            [
                {
                    "message": "multi_event_a"
                }
            ]
            """
        When I publish the multi_event_b event with the following payload
            """
            {
                "message": "multi_event_b"
            }
            """
        Then the mock TestMockService should receive 1 event
            """
            [
                {
                    "message": "multi_event_b"
                }
            ]
            """

    # ------------------------------------------------------------
    # Event type list — configuration list
    # ------------------------------------------------------------
    @single_instance
    Scenario: tests.event.list is handled for each configured event type
        When I publish the multi_event_c event with the following payload
            """
            {
                "message": "multi_event_c"
            }
            """
        Then the mock TestMockService should receive 1 event
            """
            [
                {
                    "message": "multi_event_c"
                }
            ]
            """
        When I publish the multi_event_d event with the following payload
            """
            {
                "message": "multi_event_d"
            }
            """
        Then the mock TestMockService should receive 1 event
            """
            [
                {
                    "message": "multi_event_d"
                }
            ]
            """
