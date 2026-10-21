import sys
import metac.test
import @generator_module@
import metac.module

name = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else "@module@"

with @generator@():
  with metac.module.Module(name, stateful=False, source_threshold=1024*100) as m:
    metac.test.configure_module(m)