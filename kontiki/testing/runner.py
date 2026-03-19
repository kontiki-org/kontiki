import asyncio
import logging
import threading
from concurrent.futures import Future as ConcurrentFuture

from kontiki.testing.manager import MockServiceManager

# -----------------------------------------------------------------------------
# Runner for mock service to be used in synchronous environment.
# Initially implemented for behave integration test environment.
# -----------------------------------------------------------------------------


class MockServiceRunner(threading.Thread):
    def __init__(self, mock_manager: MockServiceManager):
        super().__init__(daemon=True)
        self.mock_manager = mock_manager
        self.loop = asyncio.new_event_loop()
        self.result = None
        self.ready_event = threading.Event()
        self.stop_event = threading.Event()

    def publish(self, event_type, obj, reply_to=None, extra_headers=None):
        if extra_headers is None:
            extra_headers = {}
        # Use the runner asynchronous environment to publish input events for testing.
        logging.info("Runner publish call %s - %s", event_type, obj)

        def _publish_task():
            try:
                asyncio.create_task(
                    self.mock_manager.publish(event_type, obj, reply_to, extra_headers)
                )
                logging.info("Publish task successfully scheduled.")
            except Exception as e:
                logging.error("Failed to schedule publish task: %s", e)

        if not self.loop.is_running():
            logging.error("Event loop is not running. Cannot publish.")
            raise RuntimeError("Event loop is not running.")

        self.loop.call_soon_threadsafe(_publish_task)

    def call(self, service_name, method_name, *args, extra_headers=None, **kwargs):
        logging.info(
            "Runner remote call %s.%s with args=%s, kwargs=%s and extra_headers=%s",
            service_name,
            method_name,
            args,
            kwargs,
            extra_headers,
        )

        future = ConcurrentFuture()
        ready_event = threading.Event()

        def _done_callback(fut):
            try:
                future.set_result(fut.result())
            except Exception as e:
                future.set_exception(e)
            finally:
                ready_event.set()

        def _schedule_call():
            task = asyncio.create_task(
                self.mock_manager.call(
                    service_name,
                    method_name,
                    *args,
                    extra_headers=extra_headers,
                    **kwargs,
                )
            )
            task.add_done_callback(_done_callback)

        if not self.loop.is_running():
            logging.error("Event loop is not running. Cannot call remote method.")
            raise RuntimeError("Event loop is not running.")

        self.loop.call_soon_threadsafe(_schedule_call)

        ready_event.wait(timeout=5)
        if not future.done():
            raise TimeoutError("Remote call timed out")
        return future.result()

    # Overridden method that is called when we call start on this object (as a Thread)
    def run(self):
        # Runs the mock services within the thread.
        asyncio.set_event_loop(self.loop)

        try:
            self.result = self.loop.run_until_complete(self.mock_manager.start())
            self.ready_event.set()
            self.loop.run_until_complete(self._wait_for_stop())
            self.loop.run_until_complete(self.mock_manager.stop())
        finally:
            # Stop pending tasks before closing the loop.
            pending_tasks = asyncio.all_tasks(self.loop)
            for task in pending_tasks:
                task.cancel()
            self.loop.run_until_complete(
                asyncio.gather(*pending_tasks, return_exceptions=True)
            )
            self.loop.run_until_complete(self.loop.shutdown_asyncgens())
            self.loop.close()

    async def _wait_for_stop(self):
        while not self.stop_event.is_set():
            await asyncio.sleep(0.1)

    def stop(self):
        self.stop_event.set()
        self.join()
        self._cleanup_async_tasks()

    def _cleanup_async_tasks(self):
        try:
            # Use the runner's own event loop if it's still available
            if hasattr(self, "loop") and not self.loop.is_closed():
                try:
                    # Cancel any remaining tasks in the runner's loop
                    pending_tasks = asyncio.all_tasks(self.loop)
                    for task in pending_tasks:
                        task.cancel()
                    self.loop.run_until_complete(
                        asyncio.wait_for(
                            asyncio.gather(*pending_tasks, return_exceptions=True),
                            timeout=1.0,
                        )
                    )

                except (RuntimeError, asyncio.TimeoutError):
                    # Loop might be closed or tasks might not complete in time
                    pass
                except RuntimeError:
                    # Loop is closed, nothing more we can do
                    pass
            else:
                # Fallback: try to clean up any tasks in the current thread's event loop
                try:
                    loop = asyncio.get_running_loop()
                    pending_tasks = asyncio.all_tasks(loop)
                    for task in pending_tasks:
                        task.cancel()
                except RuntimeError:
                    # No running loop, nothing to clean up
                    pass

        except Exception:
            # Ignore any errors during cleanup to avoid masking other issues
            pass
