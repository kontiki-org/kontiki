import time

from behave import when


@when("I wait for {seconds:d} seconds")
def step_wait_for_seconds(context, seconds):
    time.sleep(seconds)
