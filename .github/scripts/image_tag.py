"""A tag kontiki-registry/x.y.z publishes ghcr.io/<owner>/kontiki-registry:<version>.

The Poetry script is the tag name with hyphens replaced by underscores
(kontiki_registry). Tags without a slash (v2.3.2) never start this workflow.
GITHUB_REF_NAME, GITHUB_REPOSITORY_OWNER and GITHUB_OUTPUT are set by Actions.
"""

import os
import re
import sys

SERVICE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
VERSION = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")


def main():
    ref = os.environ["GITHUB_REF_NAME"]
    image_name, version = ref.split("/", 1)
    if not SERVICE.match(image_name):
        print(f"Invalid service: {image_name}", file=sys.stderr)
        sys.exit(1)
    command = image_name.replace("-", "_")
    script = f"{command} ="
    with open("pyproject.toml", encoding="utf-8") as handle:
        if not any(line.startswith(script) for line in handle):
            print(f"No {command} command in pyproject.toml", file=sys.stderr)
            sys.exit(1)
    if not VERSION.match(version):
        print(f"Version must be x.y.z, got: {version}", file=sys.stderr)
        sys.exit(1)
    owner = os.environ["GITHUB_REPOSITORY_OWNER"].lower()
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as handle:
        handle.write(f"service={command}\n")
        handle.write(f"version={version}\n")
        handle.write(f"image=ghcr.io/{owner}/{image_name}:{version}\n")


if __name__ == "__main__":
    main()
