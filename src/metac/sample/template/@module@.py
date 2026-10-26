import pathlib
import metac
import metac.module
import metac.string

with metac.builder(default="@backend@"):
  with metac.module(default="@module@") as m:
    m.add(metac.string.String("String"))
