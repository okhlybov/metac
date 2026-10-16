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
    if st:
      pathlib.Path(st).touch()
    elif len(sys.argv) > 2 and not sys.argv[2].startswith("-"):
      try:
        pathlib.Path(sys.argv[2]).touch()
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

