from metac.scaffolder import cli
from metac.autotest import generate


if __name__ == "__main__":
  cli(generate, description="Generate project for the MetaC programmatic test suite", project=False)
