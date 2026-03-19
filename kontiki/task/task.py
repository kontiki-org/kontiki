import asyncio

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


def task(interval, immediate=True):
    # Mark a method as a timer. Timer will be instanciated regarding those
    # informations
    def decorator(func):
        func._task_interval = interval
        func._task_immediate = immediate
        return func

    return decorator
