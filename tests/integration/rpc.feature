Feature: RPC

    Background:
        Given the test service is running

    Scenario: RPC call with standard case
        When I call the rpc_example method with the following parameters
            """
            {
                "feature": "standard_case"
            }
            """
        Then the test service should return the result
            """
            Standard case
            """

    Scenario: RPC call with user input error
        When I call the rpc_example method with the following parameters
            """
            {
                "feature": "user_input_error"
            }
            """
        Then the test service should return the error
            """
                {
                    "code": "USER_INPUT_ERROR",
                    "message": "User input error"
                }
            """

    Scenario: RPC call with server error
        When I call the rpc_example method with the following parameters
            """
            {
                "feature": "server_error"
            }
            """
        Then the test service should return the error
            """
                {
                    "code": "INTERNAL_ERROR",
                    "message": "Unexpected Server error"
                }
            """

    Scenario: RPC call with headers
        When I call the rpc_with_headers method with the following headers
            """
            {
                "headers": {
                    "user_header": "my_user_header"
                }
            }
            """
        Then the test service should return the result
            """
            my_user_header
            """