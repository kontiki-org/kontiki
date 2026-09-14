@registry
Feature: List live instance ids for a service name

  RPC list_instances(service_name) returns the sorted list of instance_id
  values that are active or degraded. Unknown name, the registry's own
  name, or no live instance returns []. down instances are omitted.
  GET /instances/{service_name} returns the same JSON list with HTTP 200
  (including []).

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

  Scenario: list_instances returns the active instance id
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
    When I call the list_instances method with the following parameters
      """
      {
        "service_name": "RegistryTestService"
      }
      """
    Then the registry service should return the result
      """
      [
        "[REGISTRY_TEST_INSTANCE_ID]"
      ]
      """

  Scenario: GET /instances returns the same live id list
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
    When I send an HTTP GET request to "http://127.0.0.1:18082/instances/RegistryTestService"
    Then the HTTP response status should be 200
    And the HTTP response body should be
      """
      [
        "[REGISTRY_TEST_INSTANCE_ID]"
      ]
      """

  Scenario: list_instances includes a degraded instance
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
    When I call the list_instances method with the following parameters
      """
      {
        "service_name": "RegistryTestService"
      }
      """
    Then the registry service should return the result
      """
      [
        "[REGISTRY_TEST_INSTANCE_ID]"
      ]
      """

  Scenario: list_instances is empty for an unknown service
    When I call the list_instances method with the following parameters
      """
      {
        "service_name": "UnknownService"
      }
      """
    Then the registry service should return the result
      """
      []
      """

  Scenario: GET /instances is empty for an unknown service
    When I send an HTTP GET request to "http://127.0.0.1:18082/instances/UnknownService"
    Then the HTTP response status should be 200
    And the HTTP response body should be
      """
      []
      """

  Scenario: list_instances is empty for the registry's own name
    When I call the list_instances method with the following parameters
      """
      {
        "service_name": "ServiceRegistry"
      }
      """
    Then the registry service should return the result
      """
      []
      """

  Scenario: GET /instances is empty for the registry's own name
    When I send an HTTP GET request to "http://127.0.0.1:18082/instances/ServiceRegistry"
    Then the HTTP response status should be 200
    And the HTTP response body should be
      """
      []
      """

  Scenario: list_instances omits an instance that is down
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
    When I call the list_instances method with the following parameters
      """
      {
        "service_name": "RegistryTestService"
      }
      """
    Then the registry service should return the result
      """
      []
      """
