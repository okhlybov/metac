import argparse
from autoc.project.meson import generate


if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="Scaffold an AutoC Meson project")
  parser.add_argument("project", help="Project and module name")
  parser.add_argument("directory", nargs="?", default=".", help="Target directory (default: .)")
  args = parser.parse_args()
  generate(args.project, directory=args.directory)
