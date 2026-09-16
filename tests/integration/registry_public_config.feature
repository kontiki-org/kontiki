@registry
Feature: Registration exports only the top-level public mapping

    Registration sends no configuration by default. The only exported
    config is the top-level `public` mapping: if it is a non-empty
    mapping, `config` on get_services metadata and on
    registry.instance.registered is that mapping. `kontiki`, `logging`,
    and other top-level keys (for example `app`) are never exported.
    Nested keys named public (for example `app.public`) are not
    exported. `kontiki.registration.configuration.public_paths` has no
    effect.

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

    Scenario: registration metadata has no config without a public mapping
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

            app:
              smtp:
                token: super-secret

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
        Then the registry should publish the registry.instance.registered event with the following payload
            """
            {
                "service_name": "RegistryTestService",
                "instance_id": "[REGISTRY_TEST_INSTANCE_ID]",
                "host": "[REGISTRY_TEST_HOST]",
                "pid": "[REGISTRY_TEST_PID]",
                "service_version": "1.0.0",
                "kontiki_version": "[KONTIKI_VERSION]",
                "heartbeat_interval": 2,
                "group": "business",
                "timestamp": "[TIMESTAMP]"
            }
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
                        "last_heartbeat": "[TIMESTAMP]",
                        "degraded_reason": null,
                        "metadata": {
                            "service_name": "RegistryTestService",
                            "instance_id": "[REGISTRY_TEST_INSTANCE_ID]",
                            "host": "[REGISTRY_TEST_HOST]",
                            "pid": "[REGISTRY_TEST_PID]",
                            "service_version": "1.0.0",
                            "kontiki_version": "[KONTIKI_VERSION]",
                            "heartbeat_interval": 2,
                            "group": "business"
                        }
                    }
                }
            }
            """

    Scenario: a public mapping is exported as config
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

            public:
              environment: earth
              poll_interval: 30
              flags:
                new_feed: true

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
        Then the registry should publish the registry.instance.registered event with the following payload
            """
            {
                "service_name": "RegistryTestService",
                "instance_id": "[REGISTRY_TEST_INSTANCE_ID]",
                "host": "[REGISTRY_TEST_HOST]",
                "pid": "[REGISTRY_TEST_PID]",
                "service_version": "1.0.0",
                "kontiki_version": "[KONTIKI_VERSION]",
                "heartbeat_interval": 2,
                "group": "business",
                "config": {
                    "environment": "earth",
                    "poll_interval": 30,
                    "flags": {
                        "new_feed": true
                    }
                },
                "timestamp": "[TIMESTAMP]"
            }
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
                        "last_heartbeat": "[TIMESTAMP]",
                        "degraded_reason": null,
                        "metadata": {
                            "service_name": "RegistryTestService",
                            "instance_id": "[REGISTRY_TEST_INSTANCE_ID]",
                            "host": "[REGISTRY_TEST_HOST]",
                            "pid": "[REGISTRY_TEST_PID]",
                            "service_version": "1.0.0",
                            "kontiki_version": "[KONTIKI_VERSION]",
                            "heartbeat_interval": 2,
                            "group": "business",
                            "config": {
                                "environment": "earth",
                                "poll_interval": 30,
                                "flags": {
                                    "new_feed": true
                                }
                            }
                        }
                    }
                }
            }
            """

    Scenario: app secrets and kontiki keys stay off config when public is set
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

            public:
              environment: earth
              poll_interval: 30
              flags:
                new_feed: true

            app:
              smtp:
                token: super-secret

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
        Then the registry should publish the registry.instance.registered event with the following payload
            """
            {
                "service_name": "RegistryTestService",
                "instance_id": "[REGISTRY_TEST_INSTANCE_ID]",
                "host": "[REGISTRY_TEST_HOST]",
                "pid": "[REGISTRY_TEST_PID]",
                "service_version": "1.0.0",
                "kontiki_version": "[KONTIKI_VERSION]",
                "heartbeat_interval": 2,
                "group": "business",
                "config": {
                    "environment": "earth",
                    "poll_interval": 30,
                    "flags": {
                        "new_feed": true
                    }
                },
                "timestamp": "[TIMESTAMP]"
            }
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
                        "last_heartbeat": "[TIMESTAMP]",
                        "degraded_reason": null,
                        "metadata": {
                            "service_name": "RegistryTestService",
                            "instance_id": "[REGISTRY_TEST_INSTANCE_ID]",
                            "host": "[REGISTRY_TEST_HOST]",
                            "pid": "[REGISTRY_TEST_PID]",
                            "service_version": "1.0.0",
                            "kontiki_version": "[KONTIKI_VERSION]",
                            "heartbeat_interval": 2,
                            "group": "business",
                            "config": {
                                "environment": "earth",
                                "poll_interval": 30,
                                "flags": {
                                    "new_feed": true
                                }
                            }
                        }
                    }
                }
            }
            """

    Scenario: public_paths does not export configuration
        Given the registry test service is running with the following configuration
            """
            kontiki:
              amqp:
                url: amqp://guest:guest@localhost/
              registration:
                disable: false
                delay: 0
                configuration:
                  public_paths:
                    - app
                    - kontiki
              heartbeat:
                interval: 2

            app:
              smtp:
                token: super-secret

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
        Then the registry should publish the registry.instance.registered event with the following payload
            """
            {
                "service_name": "RegistryTestService",
                "instance_id": "[REGISTRY_TEST_INSTANCE_ID]",
                "host": "[REGISTRY_TEST_HOST]",
                "pid": "[REGISTRY_TEST_PID]",
                "service_version": "1.0.0",
                "kontiki_version": "[KONTIKI_VERSION]",
                "heartbeat_interval": 2,
                "group": "business",
                "timestamp": "[TIMESTAMP]"
            }
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
                        "last_heartbeat": "[TIMESTAMP]",
                        "degraded_reason": null,
                        "metadata": {
                            "service_name": "RegistryTestService",
                            "instance_id": "[REGISTRY_TEST_INSTANCE_ID]",
                            "host": "[REGISTRY_TEST_HOST]",
                            "pid": "[REGISTRY_TEST_PID]",
                            "service_version": "1.0.0",
                            "kontiki_version": "[KONTIKI_VERSION]",
                            "heartbeat_interval": 2,
                            "group": "business"
                        }
                    }
                }
            }
            """

    Scenario: a nested public key is not exported
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

            app:
              public:
                environment: earth
                poll_interval: 30
                flags:
                  new_feed: true

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
        Then the registry should publish the registry.instance.registered event with the following payload
            """
            {
                "service_name": "RegistryTestService",
                "instance_id": "[REGISTRY_TEST_INSTANCE_ID]",
                "host": "[REGISTRY_TEST_HOST]",
                "pid": "[REGISTRY_TEST_PID]",
                "service_version": "1.0.0",
                "kontiki_version": "[KONTIKI_VERSION]",
                "heartbeat_interval": 2,
                "group": "business",
                "timestamp": "[TIMESTAMP]"
            }
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
                        "last_heartbeat": "[TIMESTAMP]",
                        "degraded_reason": null,
                        "metadata": {
                            "service_name": "RegistryTestService",
                            "instance_id": "[REGISTRY_TEST_INSTANCE_ID]",
                            "host": "[REGISTRY_TEST_HOST]",
                            "pid": "[REGISTRY_TEST_PID]",
                            "service_version": "1.0.0",
                            "kontiki_version": "[KONTIKI_VERSION]",
                            "heartbeat_interval": 2,
                            "group": "business"
                        }
                    }
                }
            }
            """
