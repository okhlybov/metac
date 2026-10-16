import sys
import autoc.autotest
import @generator_module@
import autoc.module

name = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else "@module@"

with @generator@():
  with autoc.module.Module(name, stateful=False, source_threshold=1024*100) as m:
    autoc.autotest.configure_module(m)
