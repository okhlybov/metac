import sys
import pathlib

src_path = (pathlib.Path(__file__).resolve().parent / "@src_path@").resolve()
if src_path.is_dir():
  sys.path.insert(0, str(src_path))

import metac
import metac.doc
import metac.module

with metac.builder(default="@backend@"):
  with metac.module(default="@module@", stateful=False, source_count=0) as m:
    metac.doc.configure_module(m)
