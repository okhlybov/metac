from metac.scaffolder import cli
from metac.cmake import generate


if __name__ == "__main__":
  cli(generate, description="Scaffold an MetaC CMake project")
