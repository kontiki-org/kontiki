@registry
Feature: Service registry

    Services register with a logical registration group
    (kontiki.registration.group). When the key is absent, blank,
    or whitespace-only, the group is business. Any other non-empty
    string after strip is accepted (no allow-list in V1).
    The group is a first-class register field and appears in
    get_services metadata and on registry.instance.registered.

    Background:
        Given the registry service is running with the following configuration
            """
            kontiki:
              amqp:
                url: amqp://guest:guest@localhost/
              registration:
                disable: true
              http:
                address: 127.0.0.1
                port: 18082

            logging:
              version: 1
              disable_existing_loggers: True
              formatters:
                default:
                  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s - %(filename)s:%(lineno)d"
              handlers:
                console:
                  class: logging.StreamHandler
                  formatter: default
                  level: DEBUG
              loggers:
                kontiki:
                  handlers: ["console"]
                  level: DEBUG
                  propagate: False
              root:
                handlers: ["console"]
                level: DEBUG
            """
        Given the registry test service is running with the following configuration
            """
            kontiki:
              amqp:
                url: amqp://guest:guest@localhost/
              registration:
                disable: false
                delay: 0
              heartbeat:
                interval: 2

            logging:
              version: 1
              disable_existing_loggers: True
              formatters:
                default:
                  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s - %(filename)s:%(lineno)d"
              handlers:
                console:
                  class: logging.StreamHandler
                  formatter: default
                  level: DEBUG
              loggers:
                kontiki:
                  handlers: ["console"]
                  level: DEBUG
                  propagate: False
              root:
                handlers: ["console"]
                level: DEBUG
            """

    Scenario: a registered service appears as active
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
                            "heartbeat_interval": 2,
                            "group": "business"
                        }
                    }
                }
            }
            """

    Scenario: degraded heartbeat is reflected as degraded status
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
                            "heartbeat_interval": 2,
                            "group": "business"
                        }
                    }
                }
            }
            """

    Scenario: reported exception is stored in get_exceptions
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
        Then the registry should publish the registry.instance.registered event with the following payload
            """
            {
                "service_name": "RegistryTestService",
                "instance_id": "[REGISTRY_TEST_INSTANCE_ID]",
                "host": "[REGISTRY_TEST_HOST]",
                "pid": "[REGISTRY_TEST_PID]",
                "service_version": "1.0.0",
                "heartbeat_interval": 2,
                "group": "business",
                "timestamp": "[TIMESTAMP]"
            }
            """

    Scenario: a service with registration group platform exposes that group
        Given the registry test service is running with the following configuration
            """
            kontiki:
              amqp:
                url: amqp://guest:guest@localhost/
              registration:
                disable: false
                delay: 0
                group: platform
              heartbeat:
                interval: 2

            logging:
              version: 1
              disable_existing_loggers: True
              formatters:
                default:
                  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s - %(filename)s:%(lineno)d"
              handlers:
                console:
                  class: logging.StreamHandler
                  formatter: default
                  level: DEBUG
              loggers:
                kontiki:
                  handlers: ["console"]
                  level: DEBUG
                  propagate: False
              root:
                handlers: ["console"]
                level: DEBUG
            """
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
                            "heartbeat_interval": 2,
                            "group": "platform"
                        }
                    }
                }
            }
            """
        Then the registry should publish the registry.instance.registered event with the following payload
            """
            {
                "service_name": "RegistryTestService",
                "instance_id": "[REGISTRY_TEST_INSTANCE_ID]",
                "host": "[REGISTRY_TEST_HOST]",
                "pid": "[REGISTRY_TEST_PID]",
                "service_version": "1.0.0",
                "heartbeat_interval": 2,
                "group": "platform",
                "timestamp": "[TIMESTAMP]"
            }
            """

    Scenario: blank registration group is normalized to business
        Given the registry test service is running with the following configuration
            """
            kontiki:
              amqp:
                url: amqp://guest:guest@localhost/
              registration:
                disable: false
                delay: 0
                group: "   "
              heartbeat:
                interval: 2

            logging:
              version: 1
              disable_existing_loggers: True
              formatters:
                default:
                  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s - %(filename)s:%(lineno)d"
              handlers:
                console:
                  class: logging.StreamHandler
                  formatter: default
                  level: DEBUG
              loggers:
                kontiki:
                  handlers: ["console"]
                  level: DEBUG
                  propagate: False
              root:
                handlers: ["console"]
                level: DEBUG
            """
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
                            "heartbeat_interval": 2,
                            "group": "business"
                        }
                    }
                }
            }
            """
        Then the registry should publish the registry.instance.registered event with the following payload
            """
            {
                "service_name": "RegistryTestService",
                "instance_id": "[REGISTRY_TEST_INSTANCE_ID]",
                "host": "[REGISTRY_TEST_HOST]",
                "pid": "[REGISTRY_TEST_PID]",
                "service_version": "1.0.0",
                "heartbeat_interval": 2,
                "group": "business",
                "timestamp": "[TIMESTAMP]"
            }
            """

    Scenario: a custom registration group is accepted as-is
        Given the registry test service is running with the following configuration
            """
            kontiki:
              amqp:
                url: amqp://guest:guest@localhost/
              registration:
                disable: false
                delay: 0
                group: ops-mesh
              heartbeat:
                interval: 2

            logging:
              version: 1
              disable_existing_loggers: True
              formatters:
                default:
                  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s - %(filename)s:%(lineno)d"
              handlers:
                console:
                  class: logging.StreamHandler
                  formatter: default
                  level: DEBUG
              loggers:
                kontiki:
                  handlers: ["console"]
                  level: DEBUG
                  propagate: False
              root:
                handlers: ["console"]
                level: DEBUG
            """
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
                            "heartbeat_interval": 2,
                            "group": "ops-mesh"
                        }
                    }
                }
            }
            """
        Then the registry should publish the registry.instance.registered event with the following payload
            """
            {
                "service_name": "RegistryTestService",
                "instance_id": "[REGISTRY_TEST_INSTANCE_ID]",
                "host": "[REGISTRY_TEST_HOST]",
                "pid": "[REGISTRY_TEST_PID]",
                "service_version": "1.0.0",
                "heartbeat_interval": 2,
                "group": "ops-mesh",
                "timestamp": "[TIMESTAMP]"
            }
            """

    Scenario: unregistering a service publishes registry.instance.deregistered
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
