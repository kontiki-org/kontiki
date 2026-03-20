@single_instance
Feature: HTTP

    Background:
        Given the test service is running

    # ------------------------------------------------------------
    # Static endpoint
    # ------------------------------------------------------------
    Scenario: HTTP GET on static endpoint
        When I send an HTTP GET request to "/test_http"
        Then the HTTP response status should be 200
        And the HTTP response body should be
            """
            {
                "message": "Hello, from test_http!"
            }
            """

    # ------------------------------------------------------------
    # Config endpoint
    # ------------------------------------------------------------
    Scenario: HTTP GET on config endpoint
        When I send an HTTP GET request to "/test_http_entrypoint"
        Then the HTTP response status should be 200
        And the HTTP response body should be
            """
            {
                "message": "Hello, from test_http_entrypoint_from_config!"
            }
            """

    # ------------------------------------------------------------
    # Request model
    # ------------------------------------------------------------
    Scenario: HTTP POST with request model - valid payload
        When I send an HTTP POST request to "/test_http_with_request_model" with the following payload
            """
            {
                "name": "Alice",
                "age": 31
            }
            """
        Then the HTTP response status should be 200
        And the HTTP response body should be
            """
            {
                "message": "Hello, from test_http_with_request_model!"
            }
            """

    # ------------------------------------------------------------
    # Request model - invalid payload
    # ------------------------------------------------------------

    Scenario: HTTP POST with request model - invalid payload
        When I send an HTTP POST request to "/test_http_with_request_model" with the following payload
            """
            {
                "name": "Alice",
                "age": "not-an-int"
            }
            """
        Then the HTTP response status should be 500
        And the HTTP response body should contain "Internal Server Error"

    # ------------------------------------------------------------
    # Error mapping
    # ------------------------------------------------------------
    Scenario: HTTP GET with mapped application error
        When I send an HTTP GET request to "/test_http_fail"
        Then the HTTP response status should be 499
        And the HTTP response body should be
            """
            {
                "message": "Example error occurred"
            }
            """
