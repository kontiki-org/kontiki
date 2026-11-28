Feature: Messaging contracts — RPC validation

    Typed @rpc parameters are validated with TypeAdapter before the handler
    runs. Invalid arguments are a client error. Untyped parameters are
    unchanged. Return-type hints are exported later; this feature covers
    inbound args only.

    Rules locked by these scenarios:
    - A hint present → TypeAdapter.validate_python on that argument.
    - Validation failure → client error INVALID_ARGUMENT (not INTERNAL_ERROR).
    - Valid value → handler runs with the validated / coerced value (Pydantic lax).
    - No hint on a parameter → no TypeAdapter check for that parameter.
    - self, container, and _headers are never treated as typed contracts.

    Background:
        Given the test service is running

    # ------------------------------------------------------------
    # Pydantic model
    # ------------------------------------------------------------
    @single_instance
    Scenario: Valid Pydantic model argument is accepted
        When I call the rpc_typed_job method with the following parameters
            """
            {
                "job": {
                    "name": "alpha"
                }
            }
            """
        Then the test service should return the result
            """
            {
                "name": "alpha"
            }
            """

    @single_instance
    Scenario: Invalid Pydantic model argument is a client error
        When I call the rpc_typed_job method with the following parameters
            """
            {
                "job": {}
            }
            """
        Then the test service should return the error
            """
            {
                "code": "INVALID_ARGUMENT",
                "message": "Invalid argument"
            }
            """

    # ------------------------------------------------------------
    # Scalars
    # ------------------------------------------------------------
    @single_instance
    Scenario: Valid scalar arguments are accepted
        When I call the rpc_typed_scalars method with the following parameters
            """
            {
                "label": "ok",
                "count": 3
            }
            """
        Then the test service should return the result
            """
            {
                "label": "ok",
                "count": 3
            }
            """

    @single_instance
    Scenario: Invalid scalar argument is a client error
        When I call the rpc_typed_scalars method with the following parameters
            """
            {
                "label": {"not": "a string"},
                "count": 3
            }
            """
        Then the test service should return the error
            """
            {
                "code": "INVALID_ARGUMENT",
                "message": "Invalid argument"
            }
            """

    # ------------------------------------------------------------
    # Optional model
    # ------------------------------------------------------------
    @single_instance
    Scenario: Optional model null is accepted
        When I call the rpc_typed_optional_job method with the following parameters
            """
            {
                "job": null
            }
            """
        Then the test service should return the result
            """
            {
                "job": null
            }
            """

    @single_instance
    Scenario: Optional model invalid payload is a client error
        When I call the rpc_typed_optional_job method with the following parameters
            """
            {
                "job": {}
            }
            """
        Then the test service should return the error
            """
            {
                "code": "INVALID_ARGUMENT",
                "message": "Invalid argument"
            }
            """

    # ------------------------------------------------------------
    # Untyped still open
    # ------------------------------------------------------------
    @single_instance
    Scenario: Untyped RPC does not reject a free-form argument as INVALID_ARGUMENT
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
