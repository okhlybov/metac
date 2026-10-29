import os
import sys
import pathlib
from metac.scaffolder import make_template_reader
import metac.project


reader = make_template_reader(__package__)


def _python_paths():
  import metac
  metac_dir = pathlib.Path(metac.__file__).resolve().parent.parent.as_posix()

  paths = [metac_dir]
  if os.environ.get("PYTHONPATH"):
    for p in os.environ["PYTHONPATH"].split(os.pathsep):
      if p:
        p_str = pathlib.Path(p).resolve().as_posix()
        if p_str not in paths:
          paths.append(p_str)
  return paths


def _site_config():
  lines = ["# Site-local MetaC configuration - DO NOT COMMIT\n"]

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
    lines.append(f'PYTHON = "{python_exe}"\n')

  paths = _python_paths()
  sep = ";" if sys.platform == "win32" else ":"
  pythonpath_str = sep.join(paths)
  lines.append(f'METAC_PYTHONPATH = "{pythonpath_str}"\n')

  return "".join(lines)


class Scaffolder(metac.project.Scaffolder):

  # The SConstruct variable spelling of the generation modes
  _modes = {"ON": "on", "AUTO": "auto", "OFF": "off"}

  def __init__(self, resources=None, parameters=None, user_files=None):
    import metac
    metac_dir = pathlib.Path(metac.__file__).resolve().parent.parent.as_posix()

    mode = str(dict(parameters or {}).get("metac_mode", "AUTO")).upper()

    super().__init__(
      resources={
        ".metac/scons.site": _site_config(),
        "site_scons/site_tools/metac.py": reader,
        "SConstruct": reader,
        "@project@.code-workspace": reader,
        ".vscode/launch.json": reader,
        ".vscode/tasks.json": reader,
        ".gitignore": reader,
      } | (resources or {}),
      user_files=user_files,
      parameters=dict(generator="metac.scons.SCons", backend="scons", metac_path=metac_dir) | dict(parameters or {}) | {"metac_mode": self._modes.get(mode, "auto")}
    )


def generate(directory=".", project=None, upgrade=False, force=False, **kwargs):
  import metac.sample
  return metac.sample.generate(directory=directory, project=project, backend="scons", upgrade=upgrade, force=force, **kwargs)
