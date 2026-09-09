import logging

from kontiki.task.task import task


class TaskService:
    name = "TaskService"

    @task(interval=10, immediate=True)
    async def task_example(self):
        logging.info("Periodic task executed every 10 seconds.")

    @task(cron="* * * * *")
    async def cron_every_minute(self):
        logging.info("Cron task executed (every minute).")
