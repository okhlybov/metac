from metac.scaffolder import cli
from metac.project.cmake import generate


if __name__ == "__main__":
  cli(generate, description="Scaffold an MetaC CMake project", backend=False)
