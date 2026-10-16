import argparse
import autoc.project
from autoc.test import generate


if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="Generate project for the AutoC test suite")
  parser.add_argument("directory", nargs="?", default=".", help="Target directory (default: .)")
  parser.add_argument("--backend", "-b", choices=autoc.project.BACKENDS, default="cmake", help="Build backend (default: cmake)")
  args = parser.parse_args()
  generate(directory=args.directory, backend=args.backend)