import os
import sys
import pathlib
import metac.scaffolder


BACKENDS = ("cmake", "meson", "scons")


def get_backend_scaffolder(backend="cmake"):
  name = (backend or "cmake").lower()
  if name == "cmake":
    import metac.project.cmake
    return metac.project.cmake.Scaffolder
  elif name == "meson":
    import metac.project.meson
    return metac.project.meson.Scaffolder
  elif name == "scons":
    import metac.project.scons
    return metac.project.scons.Scaffolder
  else:
    raise ValueError(f"Unknown backend: '{backend}'. Available backends: {', '.join(BACKENDS)}")


class Scaffolder(metac.scaffolder.Scaffolder):

  def __init__(self, resources=None, parameters=None):
    params = dict(parameters or {})
    generator = params.get("generator", "metac.cmake.CMake")
    params.setdefault("generator", generator)
    if "generator_module" not in params:
      params["generator_module"] = generator.rpartition(".")[0] if "." in generator else generator

    import metac
    metac_dir = pathlib.Path(metac.__file__).resolve().parent.parent.as_posix()
    params.setdefault("metac_path", metac_dir)

    super().__init__(
      resources=resources,
      parameters=params,
    )

  def generate(self, target=".", upgrade=False):
    target_path = pathlib.Path(target).resolve()
    import metac
    metac_source = pathlib.Path(metac.__file__).resolve().parent.parent
    try:
      common = os.path.commonpath([str(metac_source), str(target_path)])
      if common in ("/", "\\", ""):
        self.parameters["metac_path"] = metac_source.as_posix()
      else:
        relative = os.path.relpath(metac_source, target_path)
        posix = pathlib.Path(relative).as_posix()
        self.parameters["metac_path"] = "${workspaceFolder}" if posix == "." else f"${{workspaceFolder}}/{posix}"
    except ValueError:
      self.parameters["metac_path"] = metac_source.as_posix()

    super().generate(target, upgrade=upgrade)


def generate(directory=".", project=None, backend="cmake", **kwargs):
  import metac.sample
  metac.sample.generate(directory=directory, project=project, backend=backend, **kwargs)
