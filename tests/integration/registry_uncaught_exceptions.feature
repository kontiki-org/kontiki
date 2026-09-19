@registry
Feature: Automatic uncaught exception reporting

    Uncaught exceptions in RPC, HTTP, @on_event and @task
    entrypoints are reported to the registry when
    kontiki.registration.report_uncaught_exceptions is true
    (the default). Set it to false to opt out.

    Reporting uses the same path as publish_exception /
    register_exception. The registry publishes
    registry.exception.recorded on the bus. That event is not
    stored in get_events.

    The record carries top-level exception_id, hop_id,
    entrypoint, operation and flow_id stamped from the
    handler scope. hop_id is the inbound hop of the current
    rpc or on_event handler, or null for http, task, and
    outside a handler. exception_id is a new 16-hex id at
    each record. Manual publish_exception inside a handler
    uses the same stamp.

    Mapped HTTP errors (errors= on @http), HTTP error
    responses (HTTPException), and explicit rpc_error
    returns are not uncaught exceptions and are not reported.

    Event reporting is covered by unit tests in v1 (no simple
    AMQP publisher in the @registry harness).

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
                "timestamp": "[TIMESTAMP]",
                "flow_id": "[FLOW_ID]",
                "hop_id": "[HOP_ID]",
                "exception_id": "[EXCEPTION_ID]",
                "entrypoint": "rpc",
                "operation": "raise_uncaught_exception"
            }
            """
        When I call the get_filtered_exceptions method with the following parameters
            """
            {
                "filter_field": "entrypoint",
                "value": "rpc"
            }
            """
        Then the registry service should return the result
            """
            [
                {
                    "service_name": "RegistryTestService",
                    "instance_id": "[REGISTRY_TEST_INSTANCE_ID]",
                    "exception_type": "Exception",
                    "message": "uncaught rpc exception",
                    "timestamp": "[TIMESTAMP]",
                    "flow_id": "[FLOW_ID]",
                    "hop_id": "[HOP_ID]",
                    "exception_id": "[EXCEPTION_ID]",
                    "entrypoint": "rpc",
                    "operation": "raise_uncaught_exception"
                }
            ]
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
                "timestamp": "[TIMESTAMP]",
                "flow_id": "[FLOW_ID]",
                "hop_id": null,
                "exception_id": "[EXCEPTION_ID]",
                "entrypoint": "http",
                "operation": "GET /raise_uncaught"
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

    Scenario: HTTP error response is not reported when report_uncaught_exceptions is true
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
        When I send an HTTP GET request to "/raise_http_error"
        Then the HTTP response status should be 404
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

    Scenario: returned rpc_error is not reported when report_uncaught_exceptions is true
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
        When I call the return_rpc_error method with the following parameters
            """
            {}
            """
        Then the test service should return the error
            """
            {
                "code": "CLIENT",
                "message": "rpc error"
            }
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
                "timestamp": "[TIMESTAMP]",
                "flow_id": "[FLOW_ID]",
                "hop_id": null,
                "exception_id": "[EXCEPTION_ID]",
                "entrypoint": "task",
                "operation": "raise_uncaught_task"
            }
            """
