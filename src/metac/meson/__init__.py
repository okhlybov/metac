import os
import pathlib
import metac.backend
import metac.module


class Meson:

  module = None

  def __init__(self, module=None, stamp=None):
    self.stamp = stamp
    if module is not None:
      self._generate(module, stamp=stamp)

  def _generate(self, module, stamp=None):
    meson = os.path.join(module.directory, f"{module.name}.meson")
    files = [module.header.file_name] + [s.file_name for s in module.sources]
    contents = "\n".join(files) + "\n"
    p = pathlib.Path(meson)
    if not p.exists() or p.read_text() != contents:
      p.write_text(contents)
    st = stamp or self.stamp
    if not st:
      _, _, st = metac.backend.parse()
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
        pathlib.Path(os.path.join(module.directory, f"{module.name}.stamp")).unlink(missing_ok=True)
      except OSError:
        pass

  def __enter__(self):
    self.__context = metac.module._build_context
    metac.module._build_context = self
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    if self.module:
      self._generate(self.module)
    metac.module._build_context = self.__context
    return False


import metac.project.meson

Scaffolder = metac.project.meson.Scaffolder


def generate(directory=".", project=None, backend="meson", **kwargs):
  import metac.sample
  return metac.sample.generate(directory=directory, project=project, backend=backend, **kwargs)
