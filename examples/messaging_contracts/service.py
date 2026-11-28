import logging

from pydantic import BaseModel

from kontiki.delegate import ServiceDelegate
from kontiki.messaging import rpc


class Job(BaseModel):
    name: str
    priority: int = 1


class JobAck(BaseModel):
    accepted: bool
    name: str


class ContractsExampleDelegate(ServiceDelegate):
    async def create_job(self, job, dry_run):
        logging.info("create_job name=%s dry_run=%s", job.name, dry_run)
        if dry_run:
            return JobAck(accepted=False, name=job.name)
        return JobAck(accepted=True, name=job.name)


class ContractsExampleService:
    """Registers typed RPC contracts visible on the ServiceRegistry catalog."""

    name = "ContractsExampleService"
    delegate = ContractsExampleDelegate()

    @rpc
    async def create_job(self, job: Job, dry_run: bool = False) -> JobAck:
        """Accept a typed job payload and return a typed ack."""
        return await self.delegate.create_job(job, dry_run)

    @rpc
    async def echo_label(self, label: str) -> str:
        """Echo a scalar string (schema exported on the registry)."""
        return label
