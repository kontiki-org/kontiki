import logging

from kontiki.task.task import task


class TaskService:
    name = "TaskService"

    @task(interval=10, immediate=True)
    async def task_example(self):
        logging.info("Periodic task executed every 10 seconds.")
