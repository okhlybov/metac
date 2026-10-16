import os
import sys
import pathlib
from autoc.scaffolder import make_template_reader
import autoc.project


reader = make_template_reader(__package__)


def _python_paths():
  import autoc
  autoc_dir = pathlib.Path(autoc.__file__).resolve().parent.parent.as_posix()

  paths = [autoc_dir]
  if os.environ.get("PYTHONPATH"):
    for p in os.environ["PYTHONPATH"].split(os.pathsep):
      if p:
        p_str = pathlib.Path(p).resolve().as_posix()
        if p_str not in paths:
          paths.append(p_str)
  return paths


def _site_config():
  lines = ["# Site-local AutoC configuration - DO NOT COMMIT\n"]

  import shutil
  python_cmd = shutil.which("python3") or shutil.which("python")
  cmd_path = pathlib.Path(python_cmd) if python_cmd else None
  sys_path = pathlib.Path(sys.executable)
  is_on_path = bool(
    cmd_path
    and cmd_path.resolve() == sys_path.resolve()
    and cmd_path.parent == sys_path.parent
  )
  if not is_on_path:
    python_exe = sys_path.as_posix()
    lines.append(f'set(Python_EXECUTABLE "{python_exe}" CACHE FILEPATH "Python interpreter for AutoC" FORCE)\n')

  paths = _python_paths()
  sep = ";" if sys.platform == "win32" else ":"
  pythonpath_str = sep.join(paths)
  lines.append(f'set(AUTOC_PYTHONPATH "{pythonpath_str}" CACHE STRING "Python path for AutoC generator")\n')

  return "".join(lines)


class Scaffolder(autoc.project.Scaffolder):

  def __init__(self, resources=None, parameters=None):
    import autoc
    autoc_dir = pathlib.Path(autoc.__file__).resolve().parent.parent.as_posix()

    super().__init__(
      resources={
        ".autoc/cmake.site": _site_config(),
        "cmake/AutoC.cmake": reader,
        "CMakeLists.txt": reader,
        "CMakePresets.json": reader,
        "@project@.code-workspace": reader,
        ".vscode/launch.json": reader,
        ".gitignore": reader,
      } | (resources or {}),
      parameters=dict(generator="autoc.cmake.CMake", autoc_path=autoc_dir) | dict(parameters or {})
    )


def generate(directory=".", project=None, **kwargs):
  import autoc.sample
  autoc.sample.generate(directory=directory, project=project, backend="cmake", **kwargs)
