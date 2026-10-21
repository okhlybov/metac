import sys
import os
import pathlib
import metac.module
import metac.string
import @generator_module@


os.chdir(pathlib.Path(__file__).resolve().parent)

name = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else "@module@"

with @generator@():
  with metac.module.Module(name) as m:
    m.add(metac.string.String("String"))
