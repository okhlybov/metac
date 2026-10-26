import os
import sys
import subprocess
import metac.module


class SCons:

  module = None

  def __init__(self, module=None):
    if module is not None:
      self._generate(module)

  def _generate(self, module):
    scons_file = os.path.join(module.directory, f"{module.name}.scons")
    sorted_sources = sorted(module.sources, key=lambda s: s.index)
    if sorted_sources:
      sources_repr = ",\n".join([f'  "{s.file_name}"' for s in sorted_sources])
      sources_block = f"[\n{sources_repr},\n]"
    else:
      sources_block = "[]"

    contents = f"""# MetaC generated SCons definition for {module.name}
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
    self.__context = metac.module._build_context
    metac.module._build_context = self
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    if self.module:
      self._generate(self.module)
    metac.module._build_context = self.__context
    return False


class MetaCModuleResult(list):

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


def add_metac_module(env, module, directory=".", main_dependency=None, command=None, depends=None):
  if not main_dependency:
    main_dependency = os.path.join(directory, f"{module}.py")
  if depends is None:
    depends = []

  # Determine code generation mode: AUTO, ON, or OFF
  metac_mode = env.get("METAC")
  if not metac_mode:
    try:
      _scons_script = importlib.import_module("SCons.Script")
      metac_mode = _scons_script.ARGUMENTS.get("METAC")
    except ImportError:
      pass
  if not metac_mode:
    metac_mode = os.environ.get("METAC")
  if not metac_mode:
    metac_mode = "AUTO" if os.path.exists(main_dependency) else "OFF"
  metac_mode = str(metac_mode).upper()

  module_scons = os.path.join(directory, f"{module}.scons")
  module_state = os.path.join(directory, ".metac", f"{module}.state")
  py_exec = env.get("PYTHON", sys.executable)
  if not command:
    command = [py_exec, os.path.abspath(main_dependency), module, "--backend=scons"]

  if metac_mode == "OFF":
    if not os.path.exists(module_scons):
      raise _UserError(f"MetaC: Pre-generated file '{module_scons}' not found and METAC code generation is disabled.")
  elif metac_mode in ("AUTO", "ON"):
    if not os.path.exists(main_dependency):
      if metac_mode == "AUTO" and os.path.exists(module_scons):
        pass
      else:
        raise _UserError(f"MetaC: Generation script '{main_dependency}' not found for module '{module}'.")

    need_gen = (metac_mode == "ON") or (not os.path.exists(module_scons)) or (not os.path.exists(module_state))
    if not need_gen:
      state_mtime = os.path.getmtime(module_state)
      if os.path.getmtime(main_dependency) > state_mtime:
        need_gen = True
      else:
        for dep in depends:
          if os.path.getmtime(dep) > state_mtime:
            need_gen = True
            break
    if not need_gen:
      # The generated outputs may have been removed since the last generation -
      # the state lists them, mirroring the cmake backend's missing-output check
      try:
        with open(module_state, "rt") as io:
          for line in io:
            line = line.strip()
            if not line:
              continue
            _, _, file_name = line.partition("*")
            if file_name.strip() and not os.path.exists(os.path.join(directory, file_name.strip())):
              need_gen = True
              break
      except OSError:
        pass

    if need_gen:
      print(f"-- Generating MetaC module {module}")
      env_vars = os.environ.copy()
      metac_pythonpath = env.get("METAC_PYTHONPATH")
      if metac_pythonpath:
        env_vars["PYTHONPATH"] = (
          f"{metac_pythonpath}{os.pathsep}{env_vars['PYTHONPATH']}"
          if "PYTHONPATH" in env_vars
          else metac_pythonpath
        )
      res = subprocess.run(command, cwd=directory, capture_output=True, text=True, env=env_vars)
      if res.returncode != 0:
        raise _UserError(f"MetaC generator failed for '{module}':\n{res.stderr}\n{res.stdout}")

  loc = {"env": env}
  with open(module_scons, "r") as f:
    exec(f.read(), loc)
  header = loc.get("HEADER")
  sources = loc.get("SOURCES", [])
  header_path = os.path.join(directory, header) if directory != "." else header
  source_paths = [os.path.join(directory, s) if directory != "." else s for s in sources]

  env.AppendUnique(CPPPATH=[directory])
  objs = env.Object(source_paths) if source_paths else []
  # The forced generation mode only runs the generator unconditionally - the
  # C-level build avoidance stays content-driven, matching the cmake and meson
  # backends, so recompilation happens solely when the emitted code differs
  return MetaCModuleResult(module, directory, header_path, source_paths, objs)


import metac.project.scons

Scaffolder = metac.project.scons.Scaffolder


def generate(directory=".", project=None, backend="scons", **kwargs):
  import metac.sample
  metac.sample.generate(directory=directory, project=project, backend=backend, **kwargs)
