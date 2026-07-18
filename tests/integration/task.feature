Feature: Tasks

    Periodic tasks run on a fixed interval in the service event loop.
    The interval is a literal number of seconds, or a configuration key
    (string) resolved at service start.

    Background:
        Given the test service is running

    # ------------------------------------------------------------
    # Literal interval
    # ------------------------------------------------------------
    @task_service
    Scenario: Tasks with literal interval
        When I wait for 25 seconds
        Then the mock TaskMockService should have received 5 events
            """
            [
                "task_immediate_processed",
                "task_immediate_processed",
                "task_not_immediate_processed",
                "task_immediate_processed",
                "task_not_immediate_processed"
            ]
            """

    # ------------------------------------------------------------
    # Config interval
    # ------------------------------------------------------------
    @task_config_service
    Scenario: Task with interval from tests.task.interval
        When I wait for 12 seconds
        Then the mock TaskMockService should have received 3 events
            """
            [
                "task_from_config_processed",
                "task_from_config_processed",
                "task_from_config_processed"
            ]
            """
