@registry
Feature: Automatic uncaught exception reporting

    Uncaught exceptions in RPC, HTTP and @task entrypoints are
    reported to the registry automatically when
    kontiki.registration.report_uncaught_exceptions is true
    (the default). Set it to false to opt out.

    Reporting uses the same path as publish_exception /
    register_exception, so the registry still publishes
    registry.exception.recorded with no breaking change.

    Mapped HTTP errors (errors= on @http) and explicit rpc_error
    returns are not uncaught exceptions and are not reported.

    The failing periodic task is only active in the task scenario so it
    does not pollute RPC/HTTP exception assertions.

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

    # ------------------------------------------------------------
    # Opt-out
    # ------------------------------------------------------------
    Scenario: uncaught RPC exception is not reported when report_uncaught_exceptions is false
        Given the registry test service is running with the following configuration
            """
            kontiki:
              amqp:
                url: amqp://guest:guest@localhost/
              registration:
                disable: false
                delay: 0
                report_uncaught_exceptions: false
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
        When I call the raise_uncaught_exception method with the following parameters
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
            []
            """

    # ------------------------------------------------------------
    # Default / enabled: RPC
    # ------------------------------------------------------------
    Scenario: uncaught RPC exception is reported by default
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
        When I call the raise_uncaught_exception method with the following parameters
            """
            {}
            """
        Then the registry should publish the registry.exception.recorded event with the following payload
            """
            {
                "service_name": "RegistryTestService",
                "instance_id": "[REGISTRY_TEST_INSTANCE_ID]",
                "exception_type": "Exception",
                "message": "uncaught rpc exception",
                "context": {
                    "entrypoint": "rpc",
                    "name": "raise_uncaught_exception"
                },
                "timestamp": "[TIMESTAMP]"
            }
            """

    # ------------------------------------------------------------
    # Enabled: HTTP
    # ------------------------------------------------------------
    Scenario: uncaught HTTP exception is reported when report_uncaught_exceptions is true
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
              http:
                address: "0.0.0.0"
                port: 8080

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
        When I send an HTTP GET request to "/raise_uncaught"
        Then the registry should publish the registry.exception.recorded event with the following payload
            """
            {
                "service_name": "RegistryTestService",
                "instance_id": "[REGISTRY_TEST_INSTANCE_ID]",
                "exception_type": "Exception",
                "message": "uncaught http exception",
                "context": {
                    "entrypoint": "http",
                    "method": "GET",
                    "path": "/raise_uncaught"
                },
                "timestamp": "[TIMESTAMP]"
            }
            """

    Scenario: mapped HTTP exception is not reported when report_uncaught_exceptions is true
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
              http:
                address: "0.0.0.0"
                port: 8080

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
        When I send an HTTP GET request to "/raise_mapped"
        When I call the get_filtered_exceptions method with the following parameters
            """
            {
                "filter_field": "instance_id",
                "value": "[REGISTRY_TEST_INSTANCE_ID]"
            }
            """
        Then the registry service should return the result
            """
            []
            """

    # ------------------------------------------------------------
    # Enabled: task
    # ------------------------------------------------------------
    @uncaught_task
    Scenario: uncaught task exception is reported when report_uncaught_exceptions is true
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
        When I wait for 3 seconds
        Then the registry should publish the registry.exception.recorded event with the following payload
            """
            {
                "service_name": "RegistryTestService",
                "instance_id": "[REGISTRY_TEST_INSTANCE_ID]",
                "exception_type": "Exception",
                "message": "uncaught task exception",
                "context": {
                    "entrypoint": "task",
                    "name": "raise_uncaught_task"
                },
                "timestamp": "[TIMESTAMP]"
            }
            """
