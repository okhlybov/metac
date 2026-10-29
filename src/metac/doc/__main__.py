from metac.scaffolder import cli
from metac.doc import generate


if __name__ == "__main__":
  cli(generate, description="Generate project for the MetaC documentation", project=False)
