from importlib.metadata import version, PackageNotFoundError

from metac.backend import builder

try:
  __version__ = version(__name__)
except PackageNotFoundError:
  __version__ = "dev"