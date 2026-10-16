import sys
import pathlib
import autoc.module


class Meson:

  module = None

  def __init__(self, module=None, stamp=None):
    self.stamp = stamp
    if module is not None:
      self._generate(module, stamp=stamp)

  def _generate(self, module, stamp=None):
    meson = f"{module.name}.meson"
    files = [module.header.file_name] + [s.file_name for s in module.sources]
    contents = "\n".join(files) + "\n"
    try:
      with open(meson, "r") as f:
        if not f.read() == contents:
          raise Exception()
    except Exception:
      with open(meson, "w") as f:
        f.write(contents)
    st = stamp or self.stamp
    if not st and len(sys.argv) > 2 and not sys.argv[2].startswith("-"):
      st = sys.argv[2]
    if st:
      if module.stateful:
        pathlib.Path(st).touch()
      else:
        try:
          pathlib.Path(st).unlink(missing_ok=True)
        except OSError:
          pass
    elif not module.stateful:
      try:
        pathlib.Path(f"{module.name}.stamp").unlink(missing_ok=True)
      except OSError:
        pass

  def __enter__(self):
    self.__context = autoc.module._build_context
    autoc.module._build_context = self
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    if self.module:
      self._generate(self.module)
    autoc.module._build_context = self.__context
    return False


import autoc.project.meson

Scaffolder = autoc.project.meson.Scaffolder


def generate(directory=".", project=None, backend="meson", **kwargs):
  import autoc.sample
  autoc.sample.generate(directory=directory, project=project, backend=backend, **kwargs)

