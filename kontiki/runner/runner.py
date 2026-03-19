import asyncio
import signal

from kontiki.container import ServiceContainer
from kontiki.utils import log, setup_logger

# -----------------------------------------------------------------------------


async def run_service(
    service_cls, config_paths, version, disable_service_registration=False
):
    setup_logger()
    container = ServiceContainer(
        service_cls, version, config_paths, disable_service_registration
    )
    shutdown_event = asyncio.Event()

    def setup_signal_handlers():
        # Sets up signal handlers for clean shutdown.
        # SIGTERM: Typically sent by the system when stopping the service
        # (e.g., via `kill`).
        # SIGINT: Triggered when the user presses Ctrl+C in the terminal.
        # These signals will set the `shutdown_event`, allowing the service
        # to terminate properly.

        loop = asyncio.get_running_loop()
        loop.add_signal_handler(signal.SIGTERM, shutdown_event.set)
        loop.add_signal_handler(signal.SIGINT, shutdown_event.set)

    setup_signal_handlers()

    try:
        await container.setup()
    except Exception as e:
        # Log with full traceback, then let the exception bubble up so the CLI
        # entrypoint can display a clear error message.
        log.error("Exception occurred during service setup: %s", e, exc_info=True)
        await container.stop()
        raise

    await container.start()

    try:
        await shutdown_event.wait()
    finally:
        log.info("Service shutting down")
        await container.stop()
