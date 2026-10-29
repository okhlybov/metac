import metac.project
from metac.scaffolder import make_template_reader


reader = make_template_reader(__package__)


class Scaffolder:

  def __new__(cls, resources=None, parameters=None, backend="cmake"):
    backend = (parameters or {}).get("backend") or backend
    base_cls = metac.project.get_backend_scaffolder(backend)

    custom_resources = {
      "@module@.py": reader,
      "@module@.c": reader,
    } | dict(resources or {})

    return base_cls(resources=custom_resources, parameters=parameters)

import pathlib


def generate(directory=".", project=None, backend="cmake", upgrade=False, force=False, **kwargs):
  if "directory" in kwargs:
    if directory != "." and project is None:
      project = directory
    directory = kwargs["directory"]

  if directory is None:
    directory = "."

  # If two positional arguments were passed in legacy order: generate(project, directory)
  if project is not None and isinstance(project, str) and (
    "/" in project or "\\" in project or project.startswith(".") or pathlib.Path(project).is_dir()
  ) and ("/" not in directory and "\\" not in directory and not directory.startswith(".") and not pathlib.Path(directory).is_dir()):
    directory, project = project, directory

  target_path = pathlib.Path(directory).resolve()
  project_name = project or target_path.name or "sample"
  return Scaffolder(parameters=dict(project=project_name, module=project_name), backend=backend).generate(directory, upgrade=upgrade, force=force)
