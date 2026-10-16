import os
import sys
import pathlib
import argparse
import autoc
import autoc.doc
import autoc.project
from autoc.project import BACKENDS, get_backend_scaffolder
from autoc.scaffolder import make_template_reader


reader = make_template_reader(__package__)


class Scaffolder:

  def __new__(cls, resources=None, parameters=None, backend="cmake"):
    params = dict(parameters or {})
    backend = params.get("backend") or backend
    base_cls = get_backend_scaffolder(backend)

    project = params.get("project", "doc")
    module = params.get("module", project)

    doc_pages_str = " ".join(p.resolve().as_posix() for p in autoc.doc.pages)
    doc_mainpage_str = autoc.doc.mainpage.resolve().as_posix()

    autoc_source = pathlib.Path(autoc.__file__).resolve().parent.parent

    doc_parameters = dict(
      project=project,
      module=module,
      version=autoc.__version__,
      doc_pages=doc_pages_str,
      doc_mainpage=doc_mainpage_str,
      src_path=autoc_source.as_posix(),
    )

    custom_resources = {
      "Doxyfile": reader,
      "@module@.py": reader,
      "catalog.py": reader,
      "@module@.c": None,
      ".gitignore": reader,
    } | dict(resources or {})

    class DocScaffolder(base_cls):

      def generate(self, target="."):
        target_path = pathlib.Path(target).resolve()
        autoc_source = pathlib.Path(autoc.__file__).resolve().parent.parent
        try:
          rel_path = os.path.relpath(autoc_source, target_path)
          common = os.path.commonpath([str(autoc_source), str(target_path)])
          if common in ("/", "\\", ""):
            self.parameters["src_path"] = autoc_source.as_posix()
          else:
            self.parameters["src_path"] = pathlib.Path(rel_path).as_posix()
        except ValueError:
          self.parameters["src_path"] = autoc_source.as_posix()

        super().generate(target)

    return DocScaffolder(resources=custom_resources, parameters=doc_parameters | params)


def generate(directory=".", project="doc", backend="cmake"):
  Scaffolder(parameters=dict(project=project, module=project), backend=backend).generate(directory)


if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="Generate documentation project for AutoC")
  parser.add_argument("directory", nargs="?", default=".", help="Target directory (default: .)")
  parser.add_argument("--backend", "-b", choices=BACKENDS, default="cmake", help="Build backend (default: cmake)")
  args = parser.parse_args()
  generate(directory=args.directory, backend=args.backend)
