@registry
Feature: Service registry

    Background:
        Given the registry service is running

    Scenario: a registered service appears as active
        Given the registry test service is running
        When I call the get_services method with the following parameters
            """
            {}
            """
        Then the registry service should return the result
            """
            {
                "RegistryTestService": {
                    "[REGISTRY_TEST_INSTANCE_ID]": {
                        "status": "active",
                        "metadata": {
                            "service_name": "RegistryTestService",
                            "instance_id": "[REGISTRY_TEST_INSTANCE_ID]",
                            "host": "[REGISTRY_TEST_HOST]",
                            "pid": "[REGISTRY_TEST_PID]",
                            "service_version": "1.0.0",
                            "heartbeat_interval": 2
                        }
                    }
                }
            }
            """

    Scenario: degraded heartbeat is reflected as degraded status
        Given the registry test service is running
        When I call the set_degraded method with the following parameters
            """
            {
                "degraded": true
            }
            """
        And I wait for the next registry heartbeat
        When I call the get_services method with the following parameters
            """
            {}
            """
        Then the registry service should return the result
            """
            {
                "RegistryTestService": {
                    "[REGISTRY_TEST_INSTANCE_ID]": {
                        "status": "degraded",
                        "metadata": {
                            "service_name": "RegistryTestService",
                            "instance_id": "[REGISTRY_TEST_INSTANCE_ID]",
                            "host": "[REGISTRY_TEST_HOST]",
                            "pid": "[REGISTRY_TEST_PID]",
                            "service_version": "1.0.0",
                            "heartbeat_interval": 2
                        }
                    }
                }
            }
            """

    Scenario: reported exception is stored in get_exceptions
        Given the registry test service is running
        When I call the report_test_exception method with the following parameters
            """
            {}
            """
        When I call the get_filtered_exceptions method with the following parameters
            """
            {
                "filter_field": "instance_id",
                "value": "[REGISTRY_TEST_INSTANCE_ID]"
            }
            """
        Then the registry service should return the result
            """
            [
                {
                    "service_name": "RegistryTestService",
                    "instance_id": "[REGISTRY_TEST_INSTANCE_ID]",
                    "exception_type": "Exception",
                    "message": "test exception",
                    "context": {},
                    "timestamp": "[REGISTRY_TEST_EXCEPTION_TIMESTAMP]"
                }
            ]
            """

    Scenario: registering a service publishes registry.instance.registered
        When the registry test service is running
        Then the registry should publish the registry.instance.registered event with the following payload
            """
            {
                "service_name": "RegistryTestService",
                "instance_id": "[REGISTRY_TEST_INSTANCE_ID]",
                "host": "[REGISTRY_TEST_HOST]",
                "pid": "[REGISTRY_TEST_PID]",
                "service_version": "1.0.0",
                "heartbeat_interval": 2,
                "timestamp": "[TIMESTAMP]"
            }
            """

    Scenario: unregistering a service publishes registry.instance.deregistered
        Given the registry test service is running
        When I stop the registry test service
        Then the registry should publish the registry.instance.deregistered event with the following payload
            """
            {
                "service_name": "RegistryTestService",
                "instance_id": "[REGISTRY_TEST_INSTANCE_ID]",
                "timestamp": "[TIMESTAMP]"
            }
            """

    Scenario: a healthy heartbeat publishes registry.instance.status_changed to active
        Given the registry test service is running
        And I wait for the next registry heartbeat
        Then the registry should publish the registry.instance.status_changed event with the following payload
            """
            {
                "service_name": "RegistryTestService",
                "instance_id": "[REGISTRY_TEST_INSTANCE_ID]",
                "previous_status": "down",
                "new_status": "active",
                "timestamp": "[TIMESTAMP]"
            }
            """

    Scenario: a degraded heartbeat publishes registry.instance.status_changed to degraded
        Given the registry test service is running
        And I wait for the next registry heartbeat
        When I call the set_degraded method with the following parameters
            """
            {
                "degraded": true
            }
            """
        And I wait for the next registry heartbeat
        Then the registry should publish the registry.instance.status_changed event with the following payload
            """
            {
                "service_name": "RegistryTestService",
                "instance_id": "[REGISTRY_TEST_INSTANCE_ID]",
                "previous_status": "active",
                "new_status": "degraded",
                "timestamp": "[TIMESTAMP]"
            }
            """

    Scenario: reporting an exception publishes registry.exception.recorded
        Given the registry test service is running
        When I call the report_test_exception method with the following parameters
            """
            {}
            """
        Then the registry should publish the registry.exception.recorded event with the following payload
            """
            {
                "service_name": "RegistryTestService",
                "instance_id": "[REGISTRY_TEST_INSTANCE_ID]",
                "exception_type": "Exception",
                "message": "test exception",
                "context": {},
                "timestamp": "[TIMESTAMP]"
            }
            """

    Scenario: a missed heartbeat publishes registry.instance.status_changed to down
        Given the registry test service is running
        And I wait for the next registry heartbeat
        When I kill the registry test service without unregistering
        And I wait for the next registry heartbeat
        And I wait for the next registry heartbeat
        And I wait for the next registry heartbeat
        And I wait for the next registry heartbeat
        Then the registry should publish the registry.instance.status_changed event with the following payload
            """
            {
                "service_name": "RegistryTestService",
                "instance_id": "[REGISTRY_TEST_INSTANCE_ID]",
                "previous_status": "active",
                "new_status": "down",
                "timestamp": "[TIMESTAMP]"
            }
            """
