@registry
@messaging_contracts_catalog
Feature: Messaging contracts — Registry entrypoint catalog

    Registration entrypoints include JSON Schema derived from type hints
    (TypeAdapter / Pydantic). Export is automatic when a hint is
    exportable: no flag. Untyped entrypoints stay name-only. Handler
    docstrings become description when present.

    MessagingContractsCatalogService declares the typed entrypoints under
    test for discovery. Runtime behaviour of those contracts is covered by
    the messaging_contracts_rpc and messaging_contracts_events features on
    TestService.

    Rules locked by these scenarios:
    - Typed RPC → parameters[] with name, required, default?, schema.
    - Typed return hint → return schema on the entrypoint.
    - Typed event payload → payload_schema.
    - Untyped RPC / event → no parameters / payload_schema / return keys.
    - description is the handler docstring when one exists.
    - Asserted schemas are the structural JSON Schema contract (type,
      properties, required, anyOf). Extra Pydantic keys such as title
      or $defs may be present on the wire; they are not part of the
      locked assertion surface.

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

    Scenario: Typed scalar RPC entrypoint exports parameter schemas
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
        Then the MessagingContractsCatalogService entrypoint rpc rpc_typed_scalars is
            """
            {
                "type": "rpc",
                "name": "rpc_typed_scalars",
                "handler": "rpc_typed_scalars",
                "description": "Echo typed scalar arguments.",
                "parameters": [
                    {
                        "name": "label",
                        "required": true,
                        "schema": {
                            "type": "string"
                        }
                    },
                    {
                        "name": "count",
                        "required": true,
                        "schema": {
                            "type": "integer"
                        }
                    }
                ],
                "return": {
                    "type": "object",
                    "properties": {
                        "label": {
                            "type": "string"
                        },
                        "count": {
                            "type": "integer"
                        }
                    },
                    "required": [
                        "label",
                        "count"
                    ]
                }
            }
            """

    Scenario: Typed model RPC entrypoint exports the model schema
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
        Then the MessagingContractsCatalogService entrypoint rpc rpc_typed_job is
            """
            {
                "type": "rpc",
                "name": "rpc_typed_job",
                "handler": "rpc_typed_job",
                "parameters": [
                    {
                        "name": "job",
                        "required": true,
                        "schema": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string"
                                }
                            },
                            "required": [
                                "name"
                            ]
                        }
                    }
                ]
            }
            """

    Scenario: Optional model parameter exports nullability in the schema
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
        Then the MessagingContractsCatalogService entrypoint rpc rpc_typed_optional_job is
            """
            {
                "type": "rpc",
                "name": "rpc_typed_optional_job",
                "handler": "rpc_typed_optional_job",
                "parameters": [
                    {
                        "name": "job",
                        "required": false,
                        "default": null,
                        "schema": {
                            "anyOf": [
                                {
                                    "type": "object",
                                    "properties": {
                                        "name": {
                                            "type": "string"
                                        }
                                    },
                                    "required": [
                                        "name"
                                    ]
                                },
                                {
                                    "type": "null"
                                }
                            ]
                        }
                    }
                ]
            }
            """

    Scenario: Typed event entrypoint exports payload_schema
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
        Then the MessagingContractsCatalogService entrypoint event typed_job_event is
            """
            {
                "type": "event",
                "name": "typed_job_event",
                "handler": "on_typed_job_event",
                "mode": "competing",
                "max_attempts": 3,
                "payload_schema": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string"
                        }
                    },
                    "required": [
                        "name"
                    ]
                }
            }
            """

    Scenario: Untyped RPC entrypoint stays name-only
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
        Then the MessagingContractsCatalogService entrypoint rpc return_rpc_error is
            """
            {
                "type": "rpc",
                "name": "return_rpc_error",
                "handler": "return_rpc_error"
            }
            """
