from metac.test import *
from metac.priority_queue import Queue
from metac.test.cstring import cstring, s

# The resource bearing elements exercise the move-out pop and the destroy path:
# the popped strings are released by the caller, the remaining ones by the container

x = Type(type := Queue("cstring_priority_queue", cstring))

t = type.variable("t")


x.setup(f"""
  {t.definition};
""")
x.cleanup(f"""
  {type.destroy(t)};
""")

x.unit(f"{type.push}(): push into empty queue", f"""
  {type.create(t)};
  {type.push(t, s("apple"))};
  TEST_FALSE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 1 );
  TEST_EQUAL_CHARS( {type.top_view(t)}, {s("apple")} );
""")

x.unit(f"{type.pop}(): pop returns the lexicographically greatest strings", f"""
  {type.create(t)};
  {type.push(t, s("pear"))};
  {type.push(t, s("apple"))};
  {type.push(t, s("orange"))};
  {type.push(t, s("banana"))};
  char* v;
  v = {type.pop(t)};
  TEST_EQUAL_CHARS( v, {s("pear")} );
  {cstring.destroy("v")};
  v = {type.pop(t)};
  TEST_EQUAL_CHARS( v, {s("orange")} );
  {cstring.destroy("v")};
  v = {type.pop(t)};
  TEST_EQUAL_CHARS( v, {s("banana")} );
  {cstring.destroy("v")};
  v = {type.pop(t)};
  TEST_EQUAL_CHARS( v, {s("apple")} );
  {cstring.destroy("v")};
  TEST_TRUE( {type.empty(t)} );
""")
