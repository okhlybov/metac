import sys
import metac.autotest
import @generator_module@
import metac.module

name = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else "@module@"

with @generator@():
  with metac.module.Module(name, stateful=False, source_threshold=1024*100) as m:
    metac.autotest.configure_module(m)
