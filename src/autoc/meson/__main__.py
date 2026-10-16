import argparse
from autoc.project import BACKENDS
import autoc.sample


if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="Scaffold an AutoC Meson project")
  parser.add_argument("directory", nargs="?", default=".", help="Target directory (default: .)")
  parser.add_argument("--project", "-p", default=None, help="Project and module name (default: directory name)")
  parser.add_argument("--backend", "-b", choices=BACKENDS, default="meson", help="Build backend (default: meson)")
  args = parser.parse_args()
  autoc.sample.generate(directory=args.directory, project=args.project, backend=args.backend)
