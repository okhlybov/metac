import metac
import metac.test
import metac.module

with metac.builder(default="@backend@"):
  with metac.module(default="@module@", stateful=False, source_threshold=1024*100) as m:
    metac.test.configure_module(m)