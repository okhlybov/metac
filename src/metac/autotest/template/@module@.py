import metac
import metac.autotest
import metac.module

with metac.builder(default="@backend@"):
  with metac.module(default="@module@", stateful=False, source_threshold=1024*100) as m:
    metac.autotest.configure_module(m)
