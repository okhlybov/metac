import argparse
from autoc.project import BACKENDS
from autoc.sample import generate


if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="Scaffold an AutoC sample project")
  parser.add_argument("directory", nargs="?", default=".", help="Target directory (default: .)")
  parser.add_argument("--project", "-p", default=None, help="Project and module name (default: directory name)")
  parser.add_argument("--backend", "-b", choices=BACKENDS, default="cmake", help="Build backend (default: cmake)")
  args = parser.parse_args()
  generate(directory=args.directory, project=args.project, backend=args.backend)
