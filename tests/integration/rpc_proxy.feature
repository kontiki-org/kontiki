@service_name
Feature: RpcProxy peer from configuration

    RpcProxy accepts either a static service_name or a peer key.
    peer resolves to kontiki.peers.<peer> and is preferred for
    deployment-specific identities; service_name stays for fixed
    platform targets.

    # ------------------------------------------------------------
    # Peer from kontiki.peers
    # ------------------------------------------------------------
    Scenario: RpcProxy resolves the peer service name from kontiki.peers
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
        Given a caller service is running with the following configuration
            """
            kontiki:
              service_name: rpc-proxy-caller
              amqp:
                url: amqp://guest:guest@localhost/
              registration:
                disable: true
              peers:
                target: configured-test-service

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
        When I call the call_peer_rpc_example method of rpc-proxy-caller with the following parameters
            """
            {
                "feature": "standard_case"
            }
            """
        Then rpc-proxy-caller should return the result
            """
            Standard case
            """
