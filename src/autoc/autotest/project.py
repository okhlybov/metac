import argparse
import autoc.project
from autoc.scaffolder import make_template_reader


reader = make_template_reader(__package__)


class Scaffolder:

  def __new__(cls, resources=None, parameters=None, backend="cmake"):
    backend = (parameters or {}).get("backend") or backend
    base_cls = autoc.project.get_backend_scaffolder(backend)

    custom_resources = {
      "@module@.py": reader,
      "@module@.c": None,
    } | dict(resources or {})

    params = dict(project="autoc-autotest", module="autotest") | dict(parameters or {})
    return base_cls(resources=custom_resources, parameters=params)


def generate(directory=".", backend="cmake"):
  Scaffolder(backend=backend).generate(directory)


if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="Generate project for the AutoC programmatic test suite")
  parser.add_argument("directory", nargs="?", default=".", help="Target directory (default: .)")
  parser.add_argument("--backend", "-b", choices=autoc.project.BACKENDS, default="cmake", help="Build backend (default: cmake)")
  args = parser.parse_args()
  generate(directory=args.directory, backend=args.backend)
