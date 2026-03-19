import argparse
import asyncio

from kontiki.runner.runner import run_service

# -----------------------------------------------------------------------------


def run(service_cls, description, version, disable_service_registration=False):
    parser = argparse.ArgumentParser(description=description)
    help_ = "Path to a config file. Specify multiple times for multiple files."
    parser.add_argument("--config", action="append", required=True, help=help_)
    args = parser.parse_args()

    asyncio.run(
        run_service(service_cls, args.config, version, disable_service_registration)
    )
