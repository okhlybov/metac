from metac.scaffolder import cli
from metac.meson import generate


if __name__ == "__main__":
  cli(generate, description="Scaffold an MetaC Meson project", backend="meson")
