import argparse
from metac.project.meson import generate


if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="Scaffold an MetaC Meson project")
  parser.add_argument("directory", nargs="?", default=".", help="Target directory (default: .)")
  parser.add_argument("--project", "-p", default=None, help="Project and module name (default: directory name)")
  args = parser.parse_args()
  generate(directory=args.directory, project=args.project)
