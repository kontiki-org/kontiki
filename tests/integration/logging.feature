@logging
Feature: Logging file naming

    When logging.directory is set, Kontiki names the file from
    service name and instance id. Without directory, the user
    filename is kept.

    Scenario: Kontiki imposes the log file path when directory is set
        Given a service is running with the following configuration
            """
            kontiki:
              amqp:
                url: amqp://guest:guest@localhost/
              registration:
                disable: true

            logging:
              directory: logs/integration
              handlers:
                console:
                  class: logging.StreamHandler
                  level: DEBUG
                file:
                  class: logging.FileHandler
                  level: DEBUG
              root:
                handlers: [console, file]
                level: DEBUG
            """
        Then the log file "logs/integration/ServiceNameTestService-[SHORT_INSTANCE_ID].log" exists

    Scenario: Legacy filename is kept when directory is absent
        Given a service is running with the following configuration
            """
            kontiki:
              amqp:
                url: amqp://guest:guest@localhost/
              registration:
                disable: true

            logging:
              handlers:
                console:
                  class: logging.StreamHandler
                  level: DEBUG
                file:
                  class: logging.FileHandler
                  filename: logs/integration/legacy_test_service.log
                  level: DEBUG
              root:
                handlers: [console, file]
                level: DEBUG
            """
        Then the log file "logs/integration/legacy_test_service.log" exists
