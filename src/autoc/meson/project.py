import sys
import argparse
import autoc.project
from autoc.project import BACKENDS, get_backend_scaffolder
from autoc.project.meson import Scaffolder


def generate(project, directory=".", backend="meson"):
  scaffolder_cls = get_backend_scaffolder(backend)
  scaffolder_cls(parameters=dict(project=project, module=project)).generate(directory)


if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="Scaffold an AutoC Meson project")
  parser.add_argument("project", help="Project and module name")
  parser.add_argument("directory", nargs="?", default=".", help="Target directory (default: .)")
  parser.add_argument("--backend", "-b", choices=BACKENDS, default="meson", help="Build backend (default: meson)")
  args = parser.parse_args()
  generate(args.project, directory=args.directory, backend=args.backend)
