import os
import sys


# The tool is a thin shim importing the installed package - the single source
# of the MetaC SCons logic. The interpreter running SCons is not necessarily
# the one metac is installed into, so the site-local configuration recording
# the metac location is consulted first - mirroring what the generator
# subprocess environment does with the same file
def _bootstrap_path():
  try:
    with open(os.path.join(".metac", "scons.site"), "rt") as io:
      _vars = {}
      exec(io.read(), _vars)
  except OSError:
    return
  for entry in str(_vars.get("METAC_PYTHONPATH", "")).split(os.pathsep):
    if entry and entry not in sys.path:
      sys.path.append(entry)


# SCons registers the tool module itself under the tool name before executing
# it, shadowing the real metac package for the duration of the import - the
# shadow is recognized by carrying this very file and dropped so the genuine
# package is importable
_shadow = sys.modules.get("metac")
if _shadow is not None and getattr(_shadow, "__file__", None) == __file__:
  del sys.modules["metac"]

# The toolpath may sit on sys.path while the tool executes, letting a bare
# `import metac` resolve to this very shim instead of the package and recurse -
# the entries pointing into the tool directory are excluded while the package
# is imported, since the only module needed from there is the running shim
_here = os.path.dirname(os.path.abspath(__file__))
_saved_path = sys.path[:]
sys.path[:] = [p for p in sys.path if not p or os.path.abspath(p) != _here]
try:
  try:
    import metac.scons
  except ImportError:
    _bootstrap_path()
    try:
      import metac.scons
    except ImportError as e:
      raise ImportError(
        "The MetaC SCons tool requires the metac package to be importable by "
        "the interpreter running SCons - install metac there or restore the "
        ".metac/scons.site file which records its location"
      ) from e
finally:
  sys.path[:] = _saved_path

add_metac_module = metac.scons.add_metac_module
MetaCModuleResult = metac.scons.MetaCModuleResult


def generate(env):
  env.AddMethod(add_metac_module, "MetaCModule")
  env.AddMethod(add_metac_module, "add_metac_module")


def exists(env):
  return True
