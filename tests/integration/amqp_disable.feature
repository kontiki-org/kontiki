@amqp_disable
Feature: AMQP disabled

    kontiki.amqp.disable defaults to false.

    With disable: true, the process does not connect to the broker.
    amqp.url may be omitted. The service does not register and does not
    heartbeat. @http and @task start. Declared @rpc and @on_event
    handlers are not consumed. Event types read from configuration are
    not resolved. publish and call raise AmqpDisconnectedError.

    disable: true alone is enough. required and registration.disable
    may be omitted. Startup fails when the configuration also contains
    required: true, or registration.disable: false.

    Without disable, required: false keeps its contract: the process
    takes the bus as soon as the broker answers.

    DatabaseOps exposes GET /ticks and GET /publish. The JSON body of
    GET /ticks is the number of times the periodic task has run. The
    interval comes from app.ticks.interval (seconds). The task runs
    once at startup. GET /publish calls messenger.publish and lets
    AmqpDisconnectedError propagate. The HTTP layer answers 500.

    TestService declares @rpc and @on_event handlers. Two event types
    are tests.event.name and tests.event.list. The deployment below
    does not set those keys. One HTTP route path is
    tests.http.entrypoint. That key is set, because HTTP is served.

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

    Scenario: local task and HTTP run and the service stays out of the registry
        Given a service is running with the following configuration
            """
            kontiki:
              service_name: DatabaseOps
              amqp:
                disable: true
              heartbeat:
                interval: 2
              http:
                address: 127.0.0.1
                port: 18091

            app:
              ticks:
                interval: 2

            logging:
              version: 1
              disable_existing_loggers: True
              handlers:
                console:
                  class: logging.StreamHandler
                  level: DEBUG
              root:
                handlers: [console]
                level: DEBUG
            """
        When I wait for 1 seconds
        When I send an HTTP GET request to "http://127.0.0.1:18091/ticks"
        Then the HTTP response status should be 200
        Then the HTTP response body should be
            """
            {"count": 1}
            """
        When I send an HTTP GET request to "http://127.0.0.1:18091/publish"
        Then the HTTP response status should be 500
        When I wait for the next registry heartbeat
        When I send an HTTP GET request to "http://127.0.0.1:18082/live/DatabaseOps"
        Then the HTTP response status should be 503
        When I send an HTTP GET request to "http://127.0.0.1:18091/ticks"
        Then the HTTP response status should be 200

    Scenario: declared events do not require their configuration keys
        Given the test service is running with the following configuration
            """
            kontiki:
              amqp:
                disable: true
              http:
                address: 127.0.0.1
                port: 18094

            tests:
              http:
                entrypoint: /from_config

            logging:
              version: 1
              disable_existing_loggers: True
              handlers:
                console:
                  class: logging.StreamHandler
                  level: DEBUG
              root:
                handlers: [console]
                level: DEBUG
            """
        When I send an HTTP GET request to "http://127.0.0.1:18094/test_http"
        Then the HTTP response status should be 200
        Then the HTTP response body should be
            """
            {
                "message": "Hello, from test_http!"
            }
            """

    Scenario: the process does not start when disable and required are both true
        When I start a service with the following configuration
            """
            kontiki:
              service_name: DatabaseOps
              amqp:
                disable: true
                required: true
              http:
                address: 127.0.0.1
                port: 18091

            app:
              ticks:
                interval: 2

            logging:
              version: 1
              disable_existing_loggers: True
              handlers:
                console:
                  class: logging.StreamHandler
                  level: DEBUG
              root:
                handlers: [console]
                level: DEBUG
            """
        Then the service is not running

    Scenario: the process does not start when registration is explicitly enabled
        When I start a service with the following configuration
            """
            kontiki:
              service_name: DatabaseOps
              amqp:
                disable: true
              registration:
                disable: false
              http:
                address: 127.0.0.1
                port: 18091

            app:
              ticks:
                interval: 2

            logging:
              version: 1
              disable_existing_loggers: True
              handlers:
                console:
                  class: logging.StreamHandler
                  level: DEBUG
              root:
                handlers: [console]
                level: DEBUG
            """
        Then the service is not running
