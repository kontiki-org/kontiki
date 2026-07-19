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
        Given the registry service is running

    Scenario: live probe returns 200 for the registry itself
        When I send an HTTP GET request to "http://127.0.0.1:18082/live/ServiceRegistry"
        Then the HTTP response status should be 200

    Scenario: live probe returns 200 when the service has an active instance
        Given the registry test service is registered and active
        When I send an HTTP GET request to "http://127.0.0.1:18082/live/RegistryTestService"
        Then the HTTP response status should be 200

    Scenario: live probe returns 200 when the service is degraded
        Given the registry test service is registered and degraded
        When I send an HTTP GET request to "http://127.0.0.1:18082/live/RegistryTestService"
        Then the HTTP response status should be 200

    Scenario: live probe returns 503 for an unknown service
        When I send an HTTP GET request to "http://127.0.0.1:18082/live/UnknownService"
        Then the HTTP response status should be 503

    Scenario: live probe returns 503 when all instances are down
        Given the registry test service is registered and all its instances are down
        When I send an HTTP GET request to "http://127.0.0.1:18082/live/RegistryTestService"
        Then the HTTP response status should be 503
