@registry @failed_replay
Feature: Failed messages of competing events

    FailedReplayService handles the competing event job.run with
    max_attempts 1. The handler raises, so one publish retains the
    message. The service is started by the registry test service step.

    list_failed_messages(service_name, name, limit) returns count, the
    number of retained messages, and messages, the oldest bodies up to
    limit. The call leaves the messages in place.

    replay_failed_messages(service_name, name, count) republishes the
    oldest messages, in queue order, and removes each one after the
    publish is confirmed. It returns replayed. When fewer messages are
    waiting, replayed is how many were waiting.

    drop_failed_messages(service_name, name, count) removes the oldest
    messages, in queue order, without republishing them. It returns
    dropped. When fewer messages are waiting, dropped is how many were
    waiting. A count of 0 removes nothing.

    All three calls are refused when no live instance declares that event
    as competing. Live is the same predicate as list_instances: active or
    degraded.

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

    Scenario: a live competing event with nothing retained reports empty results
        When I call the list_failed_messages method with the following parameters
            """
            {
                "service_name": "FailedReplayService",
                "name": "job.run",
                "limit": 10
            }
            """
        Then the registry service should return the result
            """
            {
                "count": 0,
                "messages": []
            }
            """
        When I call the replay_failed_messages method with the following parameters
            """
            {
                "service_name": "FailedReplayService",
                "name": "job.run",
                "count": 1
            }
            """
        Then the registry service should return the result
            """
            {
                "replayed": 0
            }
            """
        When I call the drop_failed_messages method with the following parameters
            """
            {
                "service_name": "FailedReplayService",
                "name": "job.run",
                "count": 0
            }
            """
        Then the registry service should return the result
            """
            {
                "dropped": 0
            }
            """
        When I call the drop_failed_messages method with the following parameters
            """
            {
                "service_name": "FailedReplayService",
                "name": "job.run",
                "count": 1
            }
            """
        Then the registry service should return the result
            """
            {
                "dropped": 0
            }
            """

    Scenario: listing returns the oldest retained messages and leaves them in place
        When I publish the job.run event with the following payload
            """
            {
                "job": "a"
            }
            """
        When I call the list_failed_messages method with the following parameters
            """
            {
                "service_name": "FailedReplayService",
                "name": "job.run",
                "limit": 10
            }
            """
        Then the registry service should return the result
            """
            {
                "count": 1,
                "messages": [
                    {
                        "job": "a"
                    }
                ]
            }
            """
        When I publish the job.run event with the following payload
            """
            {
                "job": "b"
            }
            """
        When I call the list_failed_messages method with the following parameters
            """
            {
                "service_name": "FailedReplayService",
                "name": "job.run",
                "limit": 1
            }
            """
        Then the registry service should return the result
            """
            {
                "count": 2,
                "messages": [
                    {
                        "job": "a"
                    }
                ]
            }
            """
        When I call the list_failed_messages method with the following parameters
            """
            {
                "service_name": "FailedReplayService",
                "name": "job.run",
                "limit": 10
            }
            """
        Then the registry service should return the result
            """
            {
                "count": 2,
                "messages": [
                    {
                        "job": "a"
                    },
                    {
                        "job": "b"
                    }
                ]
            }
            """

    Scenario: replay republishes only the messages that are waiting
        When I publish the job.run event with the following payload
            """
            {
                "job": "a"
            }
            """
        When I call the list_failed_messages method with the following parameters
            """
            {
                "service_name": "FailedReplayService",
                "name": "job.run",
                "limit": 10
            }
            """
        Then the registry service should return the result
            """
            {
                "count": 1,
                "messages": [
                    {
                        "job": "a"
                    }
                ]
            }
            """
        When I call the replay_failed_messages method with the following parameters
            """
            {
                "service_name": "FailedReplayService",
                "name": "job.run",
                "count": 5
            }
            """
        Then the registry service should return the result
            """
            {
                "replayed": 1
            }
            """

    Scenario: drop removes the oldest retained messages and leaves the rest
        When I publish the job.run event with the following payload
            """
            {
                "job": "a"
            }
            """
        When I publish the job.run event with the following payload
            """
            {
                "job": "b"
            }
            """
        When I call the list_failed_messages method with the following parameters
            """
            {
                "service_name": "FailedReplayService",
                "name": "job.run",
                "limit": 10
            }
            """
        Then the registry service should return the result
            """
            {
                "count": 2,
                "messages": [
                    {
                        "job": "a"
                    },
                    {
                        "job": "b"
                    }
                ]
            }
            """
        When I call the drop_failed_messages method with the following parameters
            """
            {
                "service_name": "FailedReplayService",
                "name": "job.run",
                "count": 1
            }
            """
        Then the registry service should return the result
            """
            {
                "dropped": 1
            }
            """
        When I call the list_failed_messages method with the following parameters
            """
            {
                "service_name": "FailedReplayService",
                "name": "job.run",
                "limit": 10
            }
            """
        Then the registry service should return the result
            """
            {
                "count": 1,
                "messages": [
                    {
                        "job": "b"
                    }
                ]
            }
            """
        When I call the drop_failed_messages method with the following parameters
            """
            {
                "service_name": "FailedReplayService",
                "name": "job.run",
                "count": 5
            }
            """
        Then the registry service should return the result
            """
            {
                "dropped": 1
            }
            """
        When I call the list_failed_messages method with the following parameters
            """
            {
                "service_name": "FailedReplayService",
                "name": "job.run",
                "limit": 10
            }
            """
        Then the registry service should return the result
            """
            {
                "count": 0,
                "messages": []
            }
            """

    Scenario: an event that no live instance declares as competing is refused
        When I call the list_failed_messages method with the following parameters
            """
            {
                "service_name": "FailedReplayService",
                "name": "other.event",
                "limit": 10
            }
            """
        Then the test service should return the error
            """
            {
                "code": "ENTRYPOINT_UNAVAILABLE",
                "message": "No live instance of FailedReplayService declares competing event other.event"
            }
            """
        When I call the replay_failed_messages method with the following parameters
            """
            {
                "service_name": "FailedReplayService",
                "name": "other.event",
                "count": 1
            }
            """
        Then the test service should return the error
            """
            {
                "code": "ENTRYPOINT_UNAVAILABLE",
                "message": "No live instance of FailedReplayService declares competing event other.event"
            }
            """
        When I call the drop_failed_messages method with the following parameters
            """
            {
                "service_name": "FailedReplayService",
                "name": "other.event",
                "count": 1
            }
            """
        Then the test service should return the error
            """
            {
                "code": "ENTRYPOINT_UNAVAILABLE",
                "message": "No live instance of FailedReplayService declares competing event other.event"
            }
            """

    Scenario: a down instance refuses list, replay, and drop
        When I kill the registry test service without unregistering
        And I wait for the next registry heartbeat
        And I wait for the next registry heartbeat
        And I wait for the next registry heartbeat
        And I wait for the next registry heartbeat
        When I call the list_failed_messages method with the following parameters
            """
            {
                "service_name": "FailedReplayService",
                "name": "job.run",
                "limit": 10
            }
            """
        Then the test service should return the error
            """
            {
                "code": "ENTRYPOINT_UNAVAILABLE",
                "message": "No live instance of FailedReplayService declares competing event job.run"
            }
            """
        When I call the replay_failed_messages method with the following parameters
            """
            {
                "service_name": "FailedReplayService",
                "name": "job.run",
                "count": 1
            }
            """
        Then the test service should return the error
            """
            {
                "code": "ENTRYPOINT_UNAVAILABLE",
                "message": "No live instance of FailedReplayService declares competing event job.run"
            }
            """
        When I call the drop_failed_messages method with the following parameters
            """
            {
                "service_name": "FailedReplayService",
                "name": "job.run",
                "count": 1
            }
            """
        Then the test service should return the error
            """
            {
                "code": "ENTRYPOINT_UNAVAILABLE",
                "message": "No live instance of FailedReplayService declares competing event job.run"
            }
            """
