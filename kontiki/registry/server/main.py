from kontiki import __version__ as kontiki_version
from kontiki.registry.server.service import ServiceRegistry
from kontiki.runner import cli


def run():
    cli.run(
        ServiceRegistry,
        "Service registry for kontiki services.",
        version=kontiki_version,
        disable_service_registration=True,
    )
