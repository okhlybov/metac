import os
import sys
import subprocess
import SCons.Script
import SCons.Errors


class AutoCModuleResult(list):

  def __init__(self, name, directory, header, sources, objects=None):
    super().__init__(sources)
    self.name = name
    self.directory = directory
    self.header = header
    self.sources = sources
    self.objects = objects or []


def add_autoc_module(env, module, directory=".", main_dependency=None, command=None, depends=None):
  if not main_dependency:
    main_dependency = os.path.join(directory, f"{module}.py")
  if depends is None:
    depends = []

  # Determine code generation mode: AUTO, ON, or OFF
  autoc_mode = env.get("AUTOC") or SCons.Script.ARGUMENTS.get("AUTOC") or os.environ.get("AUTOC")
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
      raise SCons.Errors.UserError(f"AutoC: Pre-generated file '{module_scons}' not found and AUTOC code generation is disabled.")
  elif autoc_mode in ("AUTO", "ON"):
    if not os.path.exists(main_dependency):
      if autoc_mode == "AUTO" and os.path.exists(module_scons):
        pass
      else:
        raise SCons.Errors.UserError(f"AutoC: Generation script '{main_dependency}' not found for module '{module}'.")

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
        raise SCons.Errors.UserError(f"AutoC generator failed for '{module}':\n{res.stderr}\n{res.stdout}")

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


def generate(env):
  env.AddMethod(add_autoc_module, "AutoCModule")
  env.AddMethod(add_autoc_module, "add_autoc_module")


def exists(env):
  return True
