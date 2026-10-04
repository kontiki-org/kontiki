@http_disable
Feature: HTTP disabled

    kontiki.http.disable defaults to false: declared @http routes are served.

    With disable: true, the process does not bind an HTTP port. Route paths
    read from configuration are not resolved. Other entrypoints still run.

    The service under test exposes rpc_example and HTTP routes. One route
    path is tests.http.entrypoint. This deployment does not set that key.
    The port below is the port that would have been bound.

    Scenario: the service runs without serving HTTP
        Given the test service is running with the following configuration
            """
            kontiki:
              amqp:
                url: amqp://guest:guest@localhost/
              registration:
                disable: true
              http:
                disable: true
                address: 127.0.0.1
                port: 18093

            tests:
              event:
                name: "dynamic_event_name"
                list:
                  - multi_event_c
                  - multi_event_d

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
        When I call the rpc_example method with the following parameters
            """
            {
                "feature": "standard_case"
            }
            """
        Then the test service should return the result
            """
            Standard case
            """
        When I send an HTTP GET request to "http://127.0.0.1:18093/test_http"
        Then the HTTP connection is refused
