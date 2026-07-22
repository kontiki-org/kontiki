@registry
Feature: Registry live probe

    The registry exposes a probe-friendly HTTP live check for fleet
    liveness of bus-only services. There are no in-service HTTP probes.

    GET http://127.0.0.1:18082/live/{service_name} returns 200 when at
    least one instance of the service is live (status active or
    degraded: recent heartbeat), and 503 otherwise (unknown service,
    no instance, or all instances down).

    When service_name is the registry's own name (ServiceRegistry), the
    probe returns 200 as soon as the registry HTTP server is up, without
    requiring a registered heartbeat instance.

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

    Scenario: live probe returns 200 for the registry itself
        When I send an HTTP GET request to "http://127.0.0.1:18082/live/ServiceRegistry"
        Then the HTTP response status should be 200

    Scenario: live probe returns 200 when the service has an active instance
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
        And I wait for the next registry heartbeat
        When I send an HTTP GET request to "http://127.0.0.1:18082/live/RegistryTestService"
        Then the HTTP response status should be 200

    Scenario: live probe returns 200 when the service is degraded
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
        When I call the set_degraded method with the following parameters
            """
            {
                "degraded": true
            }
            """
        And I wait for the next registry heartbeat
        When I send an HTTP GET request to "http://127.0.0.1:18082/live/RegistryTestService"
        Then the HTTP response status should be 200

    Scenario: live probe returns 503 for an unknown service
        When I send an HTTP GET request to "http://127.0.0.1:18082/live/UnknownService"
        Then the HTTP response status should be 503

    Scenario: live probe returns 503 when all instances are down
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
        And I wait for the next registry heartbeat
        When I kill the registry test service without unregistering
        And I wait for the next registry heartbeat
        And I wait for the next registry heartbeat
        And I wait for the next registry heartbeat
        And I wait for the next registry heartbeat
        When I send an HTTP GET request to "http://127.0.0.1:18082/live/RegistryTestService"
        Then the HTTP response status should be 503
