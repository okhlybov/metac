import os
import sys
import subprocess
import autoc.module


class SCons:

  module = None

  def __init__(self, module=None):
    if module is not None:
      self._generate(module)

  def _generate(self, module):
    scons_file = f"{module.name}.scons"
    sorted_sources = sorted(module.sources, key=lambda s: s.index)
    if sorted_sources:
      sources_repr = ",\n".join([f'  "{s.file_name}"' for s in sorted_sources])
      sources_block = f"[\n{sources_repr},\n]"
    else:
      sources_block = "[]"

    contents = f"""# AutoC generated SCons definition for {module.name}
Import("*") if "Import" in globals() else None

HEADER = "{module.header.file_name}"
SOURCES = {sources_block}

if "env" in globals() and SOURCES:
  OBJECTS = env.Object(SOURCES)
else:
  OBJECTS = []

if "Return" in globals():
  Return("HEADER SOURCES OBJECTS")
"""
    try:
      with open(scons_file, "r") as f:
        if not f.read() == contents:
          raise Exception()
    except Exception:
      with open(scons_file, "w") as f:
        f.write(contents)

  def __enter__(self):
    self.__context = autoc.module._build_context
    autoc.module._build_context = self
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    if self.module:
      self._generate(self.module)
    autoc.module._build_context = self.__context
    return False


class AutoCModuleResult(list):

  def __init__(self, name, directory, header, sources, objects=None):
    super().__init__(sources)
    self.name = name
    self.directory = directory
    self.header = header
    self.sources = sources
    self.objects = objects or []


import importlib

try:
  _scons_errors = importlib.import_module("SCons.Errors")
  _UserError = _scons_errors.UserError
except ImportError:
  _UserError = RuntimeError


def add_autoc_module(env, module, directory=".", main_dependency=None, command=None, depends=None):
  if not main_dependency:
    main_dependency = os.path.join(directory, f"{module}.py")
  if depends is None:
    depends = []

  # Determine code generation mode: AUTO, ON, or OFF
  autoc_mode = env.get("AUTOC")
  if not autoc_mode:
    try:
      _scons_script = importlib.import_module("SCons.Script")
      autoc_mode = _scons_script.ARGUMENTS.get("AUTOC")
    except ImportError:
      pass
  if not autoc_mode:
    autoc_mode = os.environ.get("AUTOC")
  if not autoc_mode:
    autoc_mode = "AUTO" if os.path.exists(main_dependency) else "OFF"
  autoc_mode = str(autoc_mode).upper()

  module_scons = os.path.join(directory, f"{module}.scons")
  module_state = os.path.join(directory, ".autoc", f"{module}.state")
  py_exec = env.get("PYTHON", sys.executable)
  if not command:
    command = [py_exec, os.path.abspath(main_dependency), module]

  if autoc_mode == "OFF":
    if not os.path.exists(module_scons):
      raise _UserError(f"AutoC: Pre-generated file '{module_scons}' not found and AUTOC code generation is disabled.")
  elif autoc_mode in ("AUTO", "ON"):
    if not os.path.exists(main_dependency):
      if autoc_mode == "AUTO" and os.path.exists(module_scons):
        pass
      else:
        raise _UserError(f"AutoC: Generation script '{main_dependency}' not found for module '{module}'.")

    need_gen = (autoc_mode == "ON") or (not os.path.exists(module_scons)) or (not os.path.exists(module_state))
    if not need_gen:
      state_mtime = os.path.getmtime(module_state)
      if os.path.getmtime(main_dependency) > state_mtime:
        need_gen = True
      else:
        for dep in depends:
          if os.path.getmtime(dep) > state_mtime:
            need_gen = True
            break

    if need_gen:
      print(f"-- Generating AutoC module {module}")
      env_vars = os.environ.copy()
      autoc_pythonpath = env.get("AUTOC_PYTHONPATH")
      if autoc_pythonpath:
        env_vars["PYTHONPATH"] = (
          f"{autoc_pythonpath}{os.pathsep}{env_vars['PYTHONPATH']}"
          if "PYTHONPATH" in env_vars
          else autoc_pythonpath
        )
      res = subprocess.run(command, cwd=directory, capture_output=True, text=True, env=env_vars)
      if res.returncode != 0:
        raise _UserError(f"AutoC generator failed for '{module}':\n{res.stderr}\n{res.stdout}")

  loc = {"env": env}
  with open(module_scons, "r") as f:
    exec(f.read(), loc)
  header = loc.get("HEADER")
  sources = loc.get("SOURCES", [])
  header_path = os.path.join(directory, header) if directory != "." else header
  source_paths = [os.path.join(directory, s) if directory != "." else s for s in sources]

  env.AppendUnique(CPPPATH=[directory])
  objs = env.Object(source_paths) if source_paths else []
  return AutoCModuleResult(module, directory, header_path, source_paths, objs)


import autoc.project.scons

Scaffolder = autoc.project.scons.Scaffolder


def generate(directory=".", project=None, backend="scons", **kwargs):
  import autoc.sample
  autoc.sample.generate(directory=directory, project=project, backend=backend, **kwargs)
