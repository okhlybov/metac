import argparse
import metac.project
from metac.autotest import generate


if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="Generate project for the MetaC programmatic test suite")
  parser.add_argument("directory", nargs="?", default=".", help="Target directory (default: .)")
  parser.add_argument("--backend", "-b", choices=metac.project.BACKENDS, default="cmake", help="Build backend (default: cmake)")
  args = parser.parse_args()
  generate(directory=args.directory, backend=args.backend)
