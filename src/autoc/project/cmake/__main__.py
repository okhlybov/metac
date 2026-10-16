import argparse
from autoc.project.cmake import generate


if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="Scaffold an AutoC CMake project")
  parser.add_argument("project", help="Project and module name")
  parser.add_argument("directory", nargs="?", default=".", help="Target directory (default: .)")
  args = parser.parse_args()
  generate(args.project, directory=args.directory)
