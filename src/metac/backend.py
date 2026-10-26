import os
import sys


# The build backend registry: the backend name is mapped to the module and
# the class of the generation context emitting the per-backend fragment file
_builders = {
  "cmake": ("metac.cmake", "CMake"),
  "meson": ("metac.meson", "Meson"),
  "scons": ("metac.scons", "SCons"),
}


def parse(argv=None):
  # Extract the backend selection, the module name and the stamp path from
  # the generator command line. The backend flags consume their values so
  # that the positional scan below never mistakes them for the module name
  # or the stamp; both the attached (-bNAME, --backend=NAME) and the
  # separated (-b NAME, --backend NAME) forms are recognized
  backend = module = stamp = None
  argv = list(sys.argv if argv is None else argv)
  positional = []
  i = 0
  while i < len(argv):
    token = argv[i]
    if token in ("-b", "--backend") and i + 1 < len(argv):
      backend = argv[i + 1]
      i += 2
      continue
    if token.startswith("--backend="):
      backend = token.split("=", 1)[1]
      i += 1
      continue
    if token.startswith("-b") and len(token) > 2:
      backend = token[2:]
      i += 1
      continue
    positional.append(token)
    i += 1
  named = [x for x in positional[1:] if not x.startswith("-")]
  if len(named) > 0:
    module = named[0]
  if len(named) > 1:
    stamp = named[1]
  return backend, module, stamp


def _context_class(backend):
  module_name, class_name = _builders[backend]
  return getattr(__import__(module_name, fromlist=[class_name]), class_name)


def builder(*, argv=None, default="cmake"):
  # The build backend resolution order: the command line first, then the
  # METAC_BACKEND environment variable, then the fallback - the backend the
  # project was originally scaffolded with, baked into the module script.
  # The fallback is explicitly optional and accepts either the backend name
  # or the backend context class itself, bypassing the string coercion
  backend, module, stamp = parse(argv)
  if backend is None:
    backend = os.environ.get("METAC_BACKEND")
  if backend is None:
    if isinstance(default, type):
      if default not in (_context_class(name) for name in _builders):
        raise ValueError(f"Unknown backend class: '{default.__name__}'. Available backends: {', '.join(sorted(_builders))}")
      return default()
    backend = default
  if backend not in _builders:
    raise ValueError(f"Unknown backend: '{backend}'. Available backends: {', '.join(sorted(_builders))}")
  context = _context_class(backend)
  return context(stamp=stamp) if backend == "meson" else context()
