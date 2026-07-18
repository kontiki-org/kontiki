import asyncio

from kontiki.configuration.parameter import get_parameter
from kontiki.utils import log

# -----------------------------------------------------------------------------


class Task:
    def __init__(self, interval, user_task, immediate=True):
        self.interval = interval
        self.user_task = user_task
        self.immediate = immediate
        self.running = False
        self.timer_loop_task = None

    def start(self):
        if self.running:
            log.error("Repeat task already running")
            return

        self.running = True
        self.timer_loop_task = asyncio.create_task(self._run())

    def stop(self):
        self.running = False
        if self.timer_loop_task:
            self.timer_loop_task.cancel()
            self.timer_loop_task = None

    async def _run(self):
        if self.immediate:
            await self._execute_user_task()

        while self.running:
            await asyncio.sleep(self.interval)
            await self._execute_user_task()

    async def _execute_user_task(self):
        try:
            if asyncio.iscoroutinefunction(self.user_task):
                await self.user_task()
            else:
                self.user_task()
        except Exception as e:
            log.error("Repeat task: Error executing user task: %s", e)


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
