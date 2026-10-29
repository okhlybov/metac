import os
import pathlib
import inspect
import importlib.resources
import fnmatch


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

  IGNORE_FILE = ".metacignore"

  def __init__(self, resources=None, parameters=None):
    self.resources = dict(resources or {})
    self.parameters = dict(parameters or {})
    if self.IGNORE_FILE not in self.resources:
      self.resources[self.IGNORE_FILE] = lambda _: self._default_ignore_file()

  def _default_ignore_file(self):
    module = str(self.parameters.get("module") or "")
    if "user_files" not in self.parameters and module:
      entries = [f"{module}.py", f"{module}.c"]
    else:
      entries = sorted(self.user_files)
    return "\n".join(entries) + ("\n" if entries else "")

  # The files belonging to the user rather than to the scaffolding: during
  # project seeding, these are written to .metacignore so that subsequent
  # upgrades leave them untouched. Users can customize .metacignore after
  # seeding to protect additional files from upgrade.
  @property
  def user_files(self):
    override = self.parameters.get("user_files")
    if override is not None:
      return {str(name) for name in override}
    module = str(self.parameters.get("module") or "")
    return {f"{module}.py", f"{module}.c"} if module else frozenset()

  @staticmethod
  def parse_metacignore(content):
    patterns = []
    for line in str(content).splitlines():
      line = line.strip()
      if not line or line.startswith("#"):
        continue
      patterns.append(line)
    return tuple(patterns)

  @staticmethod
  def matches_pattern(path_str, pattern):
    posix_path = path_str.replace("\\", "/").lstrip("/")
    if posix_path.startswith("./"):
      posix_path = posix_path[2:]
    pattern = pattern.replace("\\", "/")
    if pattern.startswith("./"):
      pattern = pattern[2:]
    if pattern.endswith("/"):
      return posix_path.startswith(pattern) or fnmatch.fnmatch(posix_path, pattern + "*")
    if "/" in pattern:
      return fnmatch.fnmatch(posix_path, pattern.lstrip("/"))
    return fnmatch.fnmatch(os.path.basename(posix_path), pattern) or fnmatch.fnmatch(posix_path, pattern)

  @classmethod
  def is_ignored(cls, path_str, patterns):
    ignored = False
    for pattern in patterns:
      negated = pattern.startswith("!")
      pat = pattern[1:] if negated else pattern
      if cls.matches_pattern(path_str, pat):
        ignored = not negated
    return ignored

  def generate(self, target=".", upgrade=False):
    path = pathlib.Path(target).resolve()
    path.mkdir(parents=True, exist_ok=True)
    if upgrade:
      ignore_file = path / self.IGNORE_FILE
      if not ignore_file.is_file():
        raise FileNotFoundError(f"Missing required '{self.IGNORE_FILE}' in {path}")
      with open(ignore_file, "r", encoding="utf-8") as f:
        ignore_patterns = self.parse_metacignore(f.read())
    else:
      ignore_patterns = ()

    created, refreshed, preserved, skipped = [], [], [], []
    wd = os.getcwd()
    try:
      os.chdir(path)
      for file, reader in self.resources.items():
        if not reader is None: # Override entry with value None to disable the respective file generation
          name = self.interpolate(file, self.parameters)
          exists = os.path.exists(name)
          if upgrade:
            if name == self.IGNORE_FILE or self.is_ignored(name, ignore_patterns):
              if exists:
                preserved.append(name)
              continue
          elif exists:
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