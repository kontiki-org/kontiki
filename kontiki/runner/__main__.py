#!/usr/bin/env python3
"""
Main entry point for kontiki run command.
Usage: kontiki <service_class> --config <config_file.yaml>
"""

import argparse
import asyncio
import importlib
import sys
from pathlib import Path

from kontiki.runner.runner import run_service


def import_service_class(service_class_path):
    try:
        module_path, class_name = service_class_path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        service_class = getattr(module, class_name)
        return service_class
    except (ImportError, AttributeError) as e:
        raise ImportError(f"Cannot import service class '{service_class_path}': {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Run a Kontiki service",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "service_class",
        help="Full path to the service class (e.g., 'myapp.services.MyService')",
    )

    parser.add_argument(
        "--config",
        action="append",
        required=True,
        help="Path to a config file. Specify multiple times for multiple files.",
    )

    parser.add_argument(
        "--version", default="1.0.0", help="Service version (default: 1.0.0)"
    )

    parser.add_argument(
        "--disable-service-registration",
        action="store_true",
        help="Disable automatic service registration",
    )

    args = parser.parse_args()

    # Validate config files exist
    for config_path in args.config:
        if not Path(config_path).exists():
            print(f"Error: Config file '{config_path}' does not exist", file=sys.stderr)
            sys.exit(1)

    try:
        # Import the service class
        service_class = import_service_class(args.service_class)

        # Run the service
        asyncio.run(
            run_service(
                service_class,
                args.config,
                args.version,
                args.disable_service_registration,
            )
        )
    except ImportError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nService stopped by user", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        print(f"Error running service: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
