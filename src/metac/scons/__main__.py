from metac.scaffolder import cli
from metac.scons import generate


if __name__ == "__main__":
  cli(generate, description="Scaffold an MetaC SCons project", backend="scons")
