import os
import sys
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
  user_files = ("@module@.py", "@module@.c")

  def __init__(self, resources=None, parameters=None, user_files=None):
    self.resources = dict(resources or {})
    self.parameters = dict(parameters or {})
    patterns = user_files if user_files is not None else self.parameters.get("user_files", self.user_files)
    module = str(self.parameters.get("module") or "")
    self.user_files = tuple(
      self.interpolate(f, self.parameters)
      for f in patterns
      if "@module@" not in f or module
    )
    if self.IGNORE_FILE not in self.resources:
      self.resources[self.IGNORE_FILE] = lambda _: self._default_ignore_file()

  def _default_ignore_file(self):
    entries = self.user_files
    return "\n".join(entries) + ("\n" if entries else "")

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

  def generate(self, target=".", upgrade=False, force=False):
    path = pathlib.Path(target).resolve()
    path.mkdir(parents=True, exist_ok=True)
    if upgrade:
      ignore_file = path / self.IGNORE_FILE
      if not ignore_file.is_file():
        print(f"error: Missing required '{self.IGNORE_FILE}' in '{path}'. Cannot upgrade without ignore configuration.", file=sys.stderr)
        return 1
      try:
        with open(ignore_file, "r", encoding="utf-8") as f:
          ignore_patterns = self.parse_metacignore(f.read())
      except OSError as e:
        print(f"error: Failed to read '{self.IGNORE_FILE}': {e}", file=sys.stderr)
        return 1
    else:
      ignore_patterns = ()
      if not force:
        existing = []
        for file, reader in self.resources.items():
          if reader is not None:
            name = self.interpolate(file, self.parameters)
            if (path / name).exists():
              existing.append(name)
        if existing:
          print(f"error: Refusing to overwrite existing files in '{path}':", file=sys.stderr)
          for name in sorted(existing):
            print(f"  {name}", file=sys.stderr)
          print("note: pass -f/--force to overwrite existing files, or -u/--upgrade to update scaffolding", file=sys.stderr)
          return 1

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
          (refreshed if exists else created).append(name)
          f = pathlib.Path(name)
          f.parent.mkdir(parents=True, exist_ok=True)
          with open(f, "w", encoding="utf-8") as out:
            out.write(self.interpolate(reader(file) if callable(reader) else str(reader), self.parameters))
    except OSError as e:
      print(f"error: Scaffolding failed in '{path}': {e}", file=sys.stderr)
      return 1
    finally:
      os.chdir(wd)
    self.report(path, upgrade=upgrade, created=created, refreshed=refreshed, preserved=preserved, skipped=skipped)
    return 0

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
      list_("overwritten", refreshed)
      list_("created", created)
      if skipped:
        list_("left untouched (already exist)", skipped)

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


def cli(generate, description=None, backend="cmake", project=True, args=None, exit=True):
  import argparse
  parser = argparse.ArgumentParser(description=description)
  parser.add_argument("directory", nargs="?", default=".", help="Target directory (default: .)")
  if project:
    parser.add_argument("--project", "-p", default=None, help="Project and module name (default: directory name)")
  if backend:
    backend_default = backend if isinstance(backend, str) else "cmake"
    parser.add_argument("--backend", "-b", choices=BACKENDS, default=backend_default, help=f"Build backend (default: {backend_default})")
  parser.add_argument("--upgrade", "-u", action="store_true", help="Refresh the existing scaffolding files, keeping the module and main source untouched")
  parser.add_argument("--force", "-f", action="store_true", help="Force overwriting existing files when seeding")
  parsed = parser.parse_args(args)

  kwargs = {
    "directory": parsed.directory,
    "upgrade": parsed.upgrade,
    "force": parsed.force,
  }
  if project:
    kwargs["project"] = parsed.project
  if backend:
    kwargs["backend"] = parsed.backend

  code = generate(**kwargs)
  code = 0 if code is None else code
  if exit:
    sys.exit(code)
  return code


Scaffolder.cli = staticmethod(cli)
