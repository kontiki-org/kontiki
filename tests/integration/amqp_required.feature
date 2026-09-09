@amqp_required
Feature: Optional AMQP

    kontiki.amqp.required defaults to true: if the broker is
    unreachable, setup fails and the process does not stay up.

    With required: false, HTTP and periodic tasks start even when the
    broker is unreachable. The service appears in the registry once the
    configured broker is reachable. RPC, events, and publish stay
    unavailable while it is not.

    The service under test exposes GET /ticks. The JSON body is the
    number of times the periodic task has run. The interval comes from
    app.ticks.interval (seconds). The task runs once at startup.

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

    Scenario: local task and HTTP run when the broker is unreachable
        Given a service is running with the following configuration
            """
            kontiki:
              service_name: DatabaseOps
              amqp:
                url: amqp://guest:guest@127.0.0.1:1/
                required: false
              registration:
                disable: false
                delay: 0
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
        When I send an HTTP GET request to "http://127.0.0.1:18082/live/DatabaseOps"
        Then the HTTP response status should be 503

    Scenario: the service registers when the broker is reachable
        Given a service is running with the following configuration
            """
            kontiki:
              service_name: DatabaseOps
              amqp:
                url: amqp://guest:guest@localhost/
                required: false
              registration:
                disable: false
                delay: 0
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
        And I wait for the next registry heartbeat
        When I send an HTTP GET request to "http://127.0.0.1:18082/live/DatabaseOps"
        Then the HTTP response status should be 200
        When I send an HTTP GET request to "http://127.0.0.1:18091/ticks"
        Then the HTTP response status should be 200
        Then the HTTP response body should be
            """
            {"count": 2}
            """

    Scenario: the process does not start when AMQP is required and the broker is unreachable
        When I start a service with the following configuration
            """
            kontiki:
              service_name: DatabaseOps
              amqp:
                url: amqp://guest:guest@127.0.0.1:1/
              registration:
                disable: false
                delay: 0
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
