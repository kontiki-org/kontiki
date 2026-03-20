Feature: Events

    Background:
        Given the test service is running

    Scenario: simple_event is handled and processed
        When I publish the simple_event event with the following payload
            """
            {
                "message": "Hello from integration tests"
            }
            """
        Then the mock should receive the processed payload
            """
            {
                "message": "Hello from integration tests"
            }
            """

    Scenario: tests.event.name is handled and processed
        When I publish the dynamic_event_name event with the following payload
            """
            {
                "message": "Hello from integration tests"
            }
            """
        Then the mock should receive the processed payload
            """
            {
                "message": "Hello from integration tests"
            }
            """

        Scenario: dynamic_event_name is handled and processed
        When I publish the dynamic_event_name event with the following payload
            """
            {
                "message": "Hello from integration tests"
            }
            """
        Then the mock should receive the processed payload
            """
            {
                "message": "Hello from integration tests"
            }
            """

    Scenario: retry_ok is handled and processed
        When I publish the retry_ok event with the following payload
            """
            {
                "message": "Hello from integration tests"
            }
            """
        Then the mock should receive the processed payload
            """
            {
                "message": "Hello from integration tests"
            }
            """