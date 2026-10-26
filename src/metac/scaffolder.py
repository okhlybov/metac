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

  # The files belonging to the user rather than to the scaffolding: the module
  # definition script and the main C source. Upgrade refreshes every scaffolding
  # file but never touches these, while plain generation refuses to overwrite
  # any existing file at all. Scaffolders whose module script is metac-owned
  # wiring rather than user code (test suites, documentation) override this
  # with an explicit `user_files` parameter
  @property
  def user_files(self):
    override = self.parameters.get("user_files")
    if override is not None:
      return {str(name) for name in override}
    module = str(self.parameters.get("module") or "")
    return {f"{module}.py", f"{module}.c"} if module else frozenset()

  def generate(self, target=".", upgrade=False):
    path = pathlib.Path(target).resolve()
    path.mkdir(parents=True, exist_ok=True)
    user_files = self.user_files
    created, refreshed, preserved, skipped = [], [], [], []
    wd = os.getcwd()
    try:
      os.chdir(path)
      for file, reader in self.resources.items():
        if not reader is None: # Override entry with value None to disable the respective file generation
          name = self.interpolate(file, self.parameters)
          exists = os.path.exists(name)
          if upgrade and exists and os.path.basename(name) in user_files:
            preserved.append(name)
            continue
          if exists and not upgrade:
            skipped.append(name)
            continue
          (refreshed if exists else created).append(name)
          f = pathlib.Path(name)
          f.parent.mkdir(parents=True, exist_ok=True)
          with open(f, "w", encoding="utf-8") as out:
            out.write(self.interpolate(reader(file) if callable(reader) else str(reader), self.parameters))
    finally:
      os.chdir(wd)
    self.report(path, upgrade=upgrade, created=created, refreshed=refreshed, preserved=preserved, skipped=skipped)
    return self

  # Concise per-file accounting so both the refusal and the upgrade are visible
  # from the command line; disabled resources are not accounted at all
  def report(self, path, upgrade=False, created=(), refreshed=(), preserved=(), skipped=()):
    def list_(title, names):
      if names:
        print(f"{title}:")
        for name in names:
          print(f"  {name}")
    if upgrade:
      print(f"Upgraded scaffolding in {path}")
      list_("refreshed", refreshed)
      list_("created", created)
      list_("left untouched (user files)", preserved)
    else:
      print(f"Scaffolded {path}")
      list_("created", created)
      if skipped:
        list_("left untouched (already exist)", skipped)
        print("note: pass --upgrade to refresh the existing scaffolding files")

  def interpolate(self, template, parameters=None):
    x = str(template)
    params = self.parameters | (parameters or {})
    for placeholder, value in params.items():
      x = x.replace(f"@{placeholder}@", str(value), -1)
    return x


BACKENDS = ("cmake", "meson", "scons")


def get_backend_scaffolder(backend="cmake"):
  import metac.project
  return metac.project.get_backend_scaffolder(backend)