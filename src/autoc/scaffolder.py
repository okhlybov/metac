import os
import pathlib
import inspect
import importlib.resources


#
def make_template_reader(package=None, directory="template"):
  if package is None:
    caller = inspect.currentframe().f_back
    try:
      package = caller.f_globals.get("__package__") or caller.f_globals.get("__name__")
    finally:
      del caller

  def reader(resource): return importlib.resources.files(package).joinpath(directory, resource).read_text(encoding="utf-8")

  return reader


#
class Scaffolder:
  
  def __init__(self, resources=None, parameters=None):
    self.resources = dict(resources or {})
    self.parameters = dict(parameters or {})
    
  def generate(self, target="."):
    path = pathlib.Path(target).resolve()
    path.mkdir(parents=True, exist_ok=True)
    wd = os.getcwd()
    try:
      os.chdir(path)
      for file, reader in self.resources.items():
        if not reader is None: # Override entry with value None to disable the respective file generation
          f = self.interpolate(file, self.parameters)
          pathlib.Path(f).parent.mkdir(parents=True, exist_ok=True)
          with open(f, "w", encoding="utf-8") as out:
            out.write(self.interpolate(reader(file) if callable(reader) else str(reader), self.parameters))
    finally:
      os.chdir(wd)
      
  def interpolate(self, template, parameters=None):
    x = str(template)
    params = self.parameters | (parameters or {})
    for placeholder, value in params.items():
      x = x.replace(f"@{placeholder}@", str(value), -1)
    return x


BACKENDS = ("cmake", "meson", "scons")


def get_backend_scaffolder(backend="cmake"):
  import autoc.project
  return autoc.project.get_backend_scaffolder(backend)