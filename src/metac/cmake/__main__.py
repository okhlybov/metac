import argparse
from metac.project import BACKENDS
import metac.sample


if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="Scaffold an MetaC CMake project")
  parser.add_argument("directory", nargs="?", default=".", help="Target directory (default: .)")
  parser.add_argument("--project", "-p", default=None, help="Project and module name (default: directory name)")
  parser.add_argument("--backend", "-b", choices=BACKENDS, default="cmake", help="Build backend (default: cmake)")
  args = parser.parse_args()
  metac.sample.generate(directory=args.directory, project=args.project, backend=args.backend)
