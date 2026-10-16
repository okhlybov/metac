import sys
import pathlib

src_path = (pathlib.Path(__file__).resolve().parent / "@src_path@").resolve()
if src_path.is_dir():
  sys.path.insert(0, str(src_path))

import autoc
import autoc.doc
import @generator_module@
import autoc.module

name = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else "@module@"

with @generator@():
  with autoc.module.Module(name, source_count=0) as m:
    autoc.doc.configure_module(m)
