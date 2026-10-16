import argparse
from autoc.project import generate, BACKENDS


if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="Scaffold an AutoC project")
  parser.add_argument("project", help="Project and module name")
  parser.add_argument("directory", nargs="?", default=".", help="Target directory (default: .)")
  parser.add_argument("--backend", "-b", choices=BACKENDS, default="cmake", help="Build backend (default: cmake)")
  args = parser.parse_args()
  generate(args.project, directory=args.directory, backend=args.backend)
