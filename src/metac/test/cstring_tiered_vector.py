from metac.test import *
from metac.tiered_vector import Vector
from metac.test.cstring import cstring, s

# The resource bearing elements exercise the destroy path over the chunks:
# every pushed string is released exactly once on the container destruction

x = Type(type := Vector("cstring_tiered_vector", cstring, chunk_shift=4))

t = type.variable("t")
t2 = type.variable("t2")


x.setup(f"""
  {t.definition};
  {type.create(t)};
""")
x.cleanup(f"""
  {type.destroy(t)};
""")

x.unit(f"{type.empty}(): test empty vector", f"""
  TEST_TRUE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 0 );
""")

x.unit(f"{type.push}(): push across the chunk boundaries", f"""
  {type.push(t, s("one"))};
  {type.push(t, s("two"))};
  {type.push(t, s("three"))};
  TEST_EQUAL( {type.size(t)}, 3 );
  TEST_EQUAL_CHARS( {type.view(t, 0)}, {s("one")} );
  TEST_EQUAL_CHARS( {type.view(t, 2)}, {s("three")} );
""")

x.unit(f"{type.pop}(): pop the last element", f"""
  {type.push(t, s("extra"))};
  char* v;
  v = {type.pop(t)};
  TEST_EQUAL_CHARS( v, {s("extra")} );
  {cstring.destroy("v")};
  TEST_EQUAL( {type.size(t)}, 0 );
""")


x.setup(f"""
  {t.definition};
  {t2.definition};
  {type.create(t)};
  {type.create(t2)};
""")
x.cleanup(f"""
  {type.destroy(t)};
  {type.destroy(t2)};
""")

x.unit(f"{type.copy}(): copy across chunks", f"""
  {type.push(t, s("one"))};
  {type.push(t, s("two"))};
  {type.push(t, s("three"))};
  {type.copy(t2, t)};
  TEST_TRUE( {type.equal(t, t2)} );
  TEST_EQUAL( {type.hash(t)}, {type.hash(t2)} );
  TEST_EQUAL_CHARS( {type.view(t2, 1)}, {s("two")} );
""")

x.unit(f"{type.set}(): self assignment with view", f"""
  {type.push(t, s("hello"))};
  {type.push(t, s("world"))};
  {type.set(t, 0, type.view(t, 0))};
  TEST_EQUAL_CHARS( {type.view(t, 0)}, {s("hello")} );
  {type.set(t, 0, type.view(t, 1))};
  TEST_EQUAL_CHARS( {type.view(t, 0)}, {s("world")} );
""")

x.unit(f"{type.front_view}(), {type.back_view}(), {type.clear}(): cstring access and clear", f"""
  {type.push(t, s("first"))};
  {type.push(t, s("second"))};
  {type.push(t, s("third"))};
  TEST_EQUAL_CHARS( {type.front_view(t)}, {s("first")} );
  TEST_EQUAL_CHARS( {type.back_view(t)}, {s("third")} );
  {type.clear(t)};
  TEST_TRUE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 0 );
""")
