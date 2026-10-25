import argparse
import metac.project
from metac.autotest import generate


if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="Generate project for the MetaC programmatic test suite")
  parser.add_argument("directory", nargs="?", default=".", help="Target directory (default: .)")
  parser.add_argument("--backend", "-b", choices=metac.project.BACKENDS, default="cmake", help="Build backend (default: cmake)")
  parser.add_argument("--upgrade", "-u", action="store_true", help="Refresh the existing scaffolding files, keeping the module and main source untouched")
  args = parser.parse_args()
  generate(directory=args.directory, backend=args.backend, upgrade=args.upgrade)
