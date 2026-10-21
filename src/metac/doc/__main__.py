import argparse
from metac.project import BACKENDS
from metac.doc import generate


if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="Generate documentation project for MetaC")
  parser.add_argument("directory", nargs="?", default=".", help="Target directory (default: .)")
  parser.add_argument("--backend", "-b", choices=BACKENDS, default="cmake", help="Build backend (default: cmake)")
  args = parser.parse_args()
  generate(directory=args.directory, backend=args.backend)
