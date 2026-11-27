Feature: RPC yield then continue

    An @rpc handler may yield once to send the RPC response immediately,
    then continue in the same handler on that instance (flow scope,
    work-in-flight, shutdown drain).

    Rules locked by these scenarios:
    - The first yielded value is the RPC response (including rpc_error).
    - Code after that yield runs only after the reply is sent.
    - A plain return (no yield) is unchanged — covered by Feature RPC.
    - A second yield is a continuation failure; the RPC reply already sent
      stays as the first value.
    - An exception before the yield is a normal RPC server error.
    - An exception after the yield does not change the reply already sent;
      the continuation side effect does not complete.

    Background:
        Given the test service is running

    # ------------------------------------------------------------
    # Reply before continuation
    # ------------------------------------------------------------
    @single_instance
    Scenario: RPC response is returned before the continuation finishes
        When I call the rpc_yield_continue method with the following parameters
            """
            {
                "pause_seconds": 2
            }
            """
        Then the test service should return the result
            """
            accepted
            """
        Then the mock TestMockService should receive 0 events
            """
            []
            """
        When I wait for 3 seconds
        Then the mock TestMockService should receive 1 event
            """
            [
                {
                    "status": "done"
                }
            ]
            """

    # ------------------------------------------------------------
    # Client error at admit
    # ------------------------------------------------------------
    @single_instance
    Scenario: Yielded rpc_error returns to the caller and skips continuation
        When I call the rpc_yield_continue method with the following parameters
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
        When I wait for 1 seconds
        Then the mock TestMockService should receive 0 events
            """
            []
            """

    # ------------------------------------------------------------
    # Server error before yield
    # ------------------------------------------------------------
    @single_instance
    Scenario: Exception before yield is a normal RPC server error
        When I call the rpc_yield_continue method with the following parameters
            """
            {
                "feature": "error_before_yield"
            }
            """
        Then the test service should return the error
            """
            {
                "code": "INTERNAL_ERROR",
                "message": "Boom before yield"
            }
            """
        When I wait for 1 seconds
        Then the mock TestMockService should receive 0 events
            """
            []
            """

    # ------------------------------------------------------------
    # Server error after yield
    # ------------------------------------------------------------
    @single_instance
    Scenario: Exception after yield keeps the RPC reply and skips the done side effect
        When I call the rpc_yield_continue method with the following parameters
            """
            {
                "feature": "error_after_yield"
            }
            """
        Then the test service should return the result
            """
            accepted
            """
        When I wait for 1 seconds
        Then the mock TestMockService should receive 0 events
            """
            []
            """

    # ------------------------------------------------------------
    # Second yield
    # ------------------------------------------------------------
    @single_instance
    Scenario: A second yield does not change the RPC reply already sent
        When I call the rpc_yield_continue method with the following parameters
            """
            {
                "feature": "second_yield"
            }
            """
        Then the test service should return the result
            """
            accepted
            """
        When I wait for 1 seconds
        Then the mock TestMockService should receive 0 events
            """
            []
            """
