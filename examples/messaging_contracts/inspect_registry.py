"""Print typed entrypoint contracts for ContractsExampleService from the registry.

Prerequisites:
  make run-amqp
  make run-registry
  make run-contracts-example-service

Then:
  make run-contracts-inspect-registry
"""

import asyncio
import json

from kontiki.messaging import Messenger
from kontiki.registry.client.proxy import ServiceRegistryProxy

SERVICE_NAME = "ContractsExampleService"


def _print_entrypoint(entry):
    print(json.dumps(entry, indent=2, ensure_ascii=True))
    print()


async def main():
    amqp_url = "amqp://guest:guest@localhost"
    async with Messenger(amqp_url=amqp_url, standalone=True) as messenger:
        registry = ServiceRegistryProxy(messenger)
        services = await registry.get_services()
        instances = services.get(SERVICE_NAME)
        if not instances:
            print(
                f"No live instance of {SERVICE_NAME}. "
                "Start it with: make run-contracts-example-service"
            )
            return

        instance_id, data = next(iter(instances.items()))
        print(f"{SERVICE_NAME}#{instance_id} status={data.get('status')}")
        print("Entrypoints:\n")
        for entry in data.get("metadata", {}).get("entrypoints", []):
            _print_entrypoint(entry)


if __name__ == "__main__":
    asyncio.run(main())
