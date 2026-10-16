import os
import sys
import pathlib
import autoc.scaffolder


BACKENDS = ("cmake", "meson", "scons")


def get_backend_scaffolder(backend="cmake"):
  name = (backend or "cmake").lower()
  if name == "cmake":
    import autoc.project.cmake
    return autoc.project.cmake.Scaffolder
  elif name == "meson":
    import autoc.project.meson
    return autoc.project.meson.Scaffolder
  elif name == "scons":
    import autoc.project.scons
    return autoc.project.scons.Scaffolder
  else:
    raise ValueError(f"Unknown backend: '{backend}'. Available backends: {', '.join(BACKENDS)}")


class Scaffolder(autoc.scaffolder.Scaffolder):

  def __init__(self, resources=None, parameters=None):
    params = dict(parameters or {})
    generator = params.get("generator", "autoc.cmake.CMake")
    params.setdefault("generator", generator)
    if "generator_module" not in params:
      params["generator_module"] = generator.rpartition(".")[0] if "." in generator else generator

    import autoc
    autoc_dir = pathlib.Path(autoc.__file__).resolve().parent.parent.as_posix()
    params.setdefault("autoc_path", autoc_dir)

    super().__init__(
      resources=resources,
      parameters=params,
    )

  def generate(self, target="."):
    target_path = pathlib.Path(target).resolve()
    import autoc
    autoc_source = pathlib.Path(autoc.__file__).resolve().parent.parent
    try:
      common = os.path.commonpath([str(autoc_source), str(target_path)])
      if common in ("/", "\\", ""):
        self.parameters["autoc_path"] = autoc_source.as_posix()
      else:
        relative = os.path.relpath(autoc_source, target_path)
        posix = pathlib.Path(relative).as_posix()
        self.parameters["autoc_path"] = "${workspaceFolder}" if posix == "." else f"${{workspaceFolder}}/{posix}"
    except ValueError:
      self.parameters["autoc_path"] = autoc_source.as_posix()

    super().generate(target)


def generate(directory=".", project=None, backend="cmake", **kwargs):
  import autoc.sample
  autoc.sample.generate(directory=directory, project=project, backend=backend, **kwargs)
