import argparse
from metac.project import BACKENDS
from metac.sample import generate


if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="Scaffold an MetaC sample project")
  parser.add_argument("directory", nargs="?", default=".", help="Target directory (default: .)")
  parser.add_argument("--project", "-p", default=None, help="Project and module name (default: directory name)")
  parser.add_argument("--backend", "-b", choices=BACKENDS, default="cmake", help="Build backend (default: cmake)")
  parser.add_argument("--upgrade", "-u", action="store_true", help="Refresh the existing scaffolding files, keeping the module and main source untouched")
  args = parser.parse_args()
  generate(directory=args.directory, project=args.project, backend=args.backend, upgrade=args.upgrade)
