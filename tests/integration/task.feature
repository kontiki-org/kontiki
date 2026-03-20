@task_service
Feature: Tasks

    Background:
        Given the test service is running

    Scenario: Tasks 
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