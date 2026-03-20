import time

from kontiki.testing import MockServiceManager, MockServiceRunner


def before_all(context):
    # Wait for the service to be ready
    time.sleep(2)

    # Setup and start the mock service manager and runner
    context.manager = MockServiceManager(log_file="integration.log")
    context.runner = MockServiceRunner(context.manager)
    context.runner.start()
    context.runner.ready_event.wait(timeout=10)


def after_all(context):
    if context.runner is not None:
        context.runner.stop()
