import os
import sys
import subprocess
import SCons.Script
import SCons.Errors


class MetaCModuleResult(list):

  def __init__(self, name, directory, header, sources, objects=None):
    super().__init__(sources)
    self.name = name
    self.directory = directory
    self.header = header
    self.sources = sources
    self.objects = objects or []


def add_metac_module(env, module, directory=".", main_dependency=None, command=None, depends=None):
  if not main_dependency:
    main_dependency = os.path.join(directory, f"{module}.py")
  if depends is None:
    depends = []

  # Determine code generation mode: AUTO, ON, or OFF
  metac_mode = env.get("METAC") or SCons.Script.ARGUMENTS.get("METAC") or os.environ.get("METAC")
  if not metac_mode:
    metac_mode = "AUTO" if os.path.exists(main_dependency) else "OFF"
  metac_mode = str(metac_mode).upper()

  module_scons = os.path.join(directory, f"{module}.scons")
  module_state = os.path.join(directory, ".metac", f"{module}.state")
  py_exec = env.get("PYTHON", sys.executable)
  if not command:
    command = [py_exec, os.path.abspath(main_dependency), module]

  if metac_mode == "OFF":
    if not os.path.exists(module_scons):
      raise SCons.Errors.UserError(f"MetaC: Pre-generated file '{module_scons}' not found and METAC code generation is disabled.")
  elif metac_mode in ("AUTO", "ON"):
    if not os.path.exists(main_dependency):
      if metac_mode == "AUTO" and os.path.exists(module_scons):
        pass
      else:
        raise SCons.Errors.UserError(f"MetaC: Generation script '{main_dependency}' not found for module '{module}'.")

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
        raise SCons.Errors.UserError(f"MetaC generator failed for '{module}':\n{res.stderr}\n{res.stdout}")

  loc = {"env": env}
  with open(module_scons, "r") as f:
    exec(f.read(), loc)
  header = loc.get("HEADER")
  sources = loc.get("SOURCES", [])
  header_path = os.path.join(directory, header) if directory != "." else header
  source_paths = [os.path.join(directory, s) if directory != "." else s for s in sources]

  env.AppendUnique(CPPPATH=[directory])
  objs = env.Object(source_paths) if source_paths else []
  return MetaCModuleResult(module, directory, header_path, source_paths, objs)


def generate(env):
  env.AddMethod(add_metac_module, "MetaCModule")
  env.AddMethod(add_metac_module, "add_metac_module")


def exists(env):
  return True
