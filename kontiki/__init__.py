import os

__all__ = ["__version__"]

image_version = os.environ.get("KONTIKI_VERSION", "")
__version__ = image_version or "2.3.2"
