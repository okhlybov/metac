import sys
import os
import pathlib
import autoc.module
import autoc.string
import @generator_module@


os.chdir(pathlib.Path(__file__).resolve().parent)

name = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else "@module@"

with @generator@():
  with autoc.module.Module(name) as m:
    m.add(autoc.string.String("String"))
