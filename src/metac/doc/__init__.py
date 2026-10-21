import os
import pathlib
import metac
import metac.project
from metac.scaffolder import make_template_reader
from metac.doc.catalog import *

dir = pathlib.Path(__file__).parent
mainpage = dir / "mainpage.md"
pages = [
  dir / "mainpage.md",
  dir / "tutorial.md",
  dir / "design.md",
  dir / "containers.md",
]

reader = make_template_reader(__package__)


class Scaffolder:

  def __new__(cls, resources=None, parameters=None, backend="cmake"):
    params = dict(parameters or {})
    backend = params.get("backend") or backend
    base_cls = metac.project.get_backend_scaffolder(backend)

    project = params.get("project", "doc")
    module = params.get("module", project)

    doc_pages_str = " ".join(p.resolve().as_posix() for p in pages)
    doc_mainpage_str = mainpage.resolve().as_posix()

    metac_source = pathlib.Path(metac.__file__).resolve().parent.parent

    doc_parameters = dict(
      project=project,
      module=module,
      version=metac.__version__,
      doc_pages=doc_pages_str,
      doc_mainpage=doc_mainpage_str,
      src_path=metac_source.as_posix(),
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
        metac_source = pathlib.Path(metac.__file__).resolve().parent.parent
        try:
          rel_path = os.path.relpath(metac_source, target_path)
          common = os.path.commonpath([str(metac_source), str(target_path)])
          if common in ("/", "\\", ""):
            self.parameters["src_path"] = metac_source.as_posix()
          else:
            self.parameters["src_path"] = pathlib.Path(rel_path).as_posix()
        except ValueError:
          self.parameters["src_path"] = metac_source.as_posix()

        super().generate(target)

    return DocScaffolder(resources=custom_resources, parameters=doc_parameters | params)


def generate(directory=".", project="doc", backend="cmake"):
  Scaffolder(parameters=dict(project=project, module=project), backend=backend).generate(directory)
