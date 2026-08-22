@service_name
Feature: Configurable service name

    The logical service name used for RPC queues and the registry is
    kontiki.service_name when set, otherwise the class name attribute,
    otherwise the Python class name.

    # ------------------------------------------------------------
    # Override from configuration
    # ------------------------------------------------------------
    Scenario: RPC is exposed under kontiki.service_name
        Given a service is running with the following configuration
            """
            kontiki:
              service_name: configured-test-service
              amqp:
                url: amqp://guest:guest@localhost/
              registration:
                disable: true

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
        When I call the rpc_example method of configured-test-service with the following parameters
            """
            {
                "feature": "standard_case"
            }
            """
        Then configured-test-service should return the result
            """
            Standard case
            """
