import asyncio

from kontiki.configuration.parameter import get_parameter
from kontiki.messaging.flow import enter_flow_context, reset_flow_id
from kontiki.utils import log

# -----------------------------------------------------------------------------


class Task:
    def __init__(self, interval, user_task, immediate=True, container=None):
        self.interval = interval
        self.user_task = user_task
        self.immediate = immediate
        self.container = container
        self.running = False
        self.timer_loop_task = None
        self._current_iteration = None

    def start(self):
        if self.running:
            log.error("Repeat task already running")
            return

        self.running = True
        self.timer_loop_task = asyncio.create_task(self._run())

    def stop_accepting(self):
        self.running = False

    async def drain(self):
        if self._current_iteration is not None:
            try:
                await self._current_iteration
            except asyncio.CancelledError:
                pass

    async def force_stop(self):
        if self.timer_loop_task and not self.timer_loop_task.done():
            self.timer_loop_task.cancel()
            try:
                await self.timer_loop_task
            except asyncio.CancelledError:
                pass
            self.timer_loop_task = None

        if self._current_iteration is not None and not self._current_iteration.done():
            self._current_iteration.cancel()
            try:
                await self._current_iteration
            except asyncio.CancelledError:
                pass

    def stop(self):
        self.stop_accepting()
        if self.timer_loop_task:
            self.timer_loop_task.cancel()
            self.timer_loop_task = None

    async def _run(self):
        if self.immediate:
            await self._execute_user_task()

        while self.running:
            await asyncio.sleep(self.interval)
            if not self.running:
                break
            await self._execute_user_task()

    async def _execute_user_task(self):
        self._current_iteration = asyncio.current_task()
        flow_token = enter_flow_context(None)
        try:
            try:
                if asyncio.iscoroutinefunction(self.user_task):
                    await self.user_task()
                else:
                    self.user_task()
            except Exception as e:
                log.error("Repeat task: Error executing user task: %s", e)
                if self.container is not None:
                    await self.container.report_uncaught_exception(
                        e,
                        {
                            "entrypoint": "task",
                            "name": self.user_task.__name__,
                        },
                    )
        finally:
            reset_flow_id(flow_token)
            self._current_iteration = None


def resolve_task_interval(config, interval):
    if type(interval) in (int, float):
        return interval
    if isinstance(interval, str):
        value = get_parameter(config, interval)
        if type(value) not in (int, float):
            raise TypeError(
                f"Task interval '{interval}' must resolve to a number, "
                f"got {type(value).__name__}."
            )
        return value
    raise TypeError(
        f"Task interval must be a number or config key string, "
        f"got {type(interval).__name__}."
    )


def task(interval, immediate=True):
    if type(interval) not in (int, float) and not isinstance(interval, str):
        raise TypeError(
            f"Task interval must be a number or config key string, "
            f"got {type(interval).__name__}."
        )

    def decorator(func):
        func._task_interval = interval
        func._task_immediate = immediate
        return func

    return decorator
