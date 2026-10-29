from metac.scaffolder import cli
from metac.test import generate


if __name__ == "__main__":
  cli(generate, description="Generate project for the MetaC test suite", project=False)
