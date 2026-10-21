from metac.test import *
from metac.flat_map import Map
from metac.test.cstring import cstring, s

x = Type(type := Map("flat_cstring_int_map", "int", cstring))

t = type.variable("t")

range = type.range
r = range.variable("r")

x.setup(f"""
  {t.definition};
""")
x.cleanup(f"""
  {type.destroy(t)};
""")

x.unit(f"{type.set}(): set into empty map", f"""
  {type.create(t)};
  TEST_TRUE( {type.empty(t)} );
  {type.set(t, s("apple"), 1)};
  TEST_FALSE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 1 );
  TEST_EQUAL( {type.get(t, s("apple"))}, 1 );
""")

x.unit(f"{type.set}(): overwrite existing entry", f"""
  {type.create(t)};
  {type.set(t, s("apple"), 1)};
  {type.set(t, s("apple"), 10)};
  TEST_EQUAL( {type.size(t)}, 1 );
  TEST_EQUAL( {type.get(t, s("apple"))}, 10 );
""")

x.unit(f"{type.indexed}(): indexed and view lookup", f"""
  {type.create(t)};
  {type.set(t, s("cherry"), 3)};
  {type.set(t, s("apple"), 1)};
  {type.set(t, s("banana"), 2)};
  TEST_TRUE( {type.indexed(t, s("apple"))} );
  TEST_TRUE( {type.indexed(t, s("banana"))} );
  TEST_TRUE( {type.indexed(t, s("cherry"))} );
  TEST_FALSE( {type.indexed(t, s("date"))} );
  TEST_NOT_NULL( {type.view(t, s("banana"))} );
  TEST_EQUAL( *{type.view(t, s("banana"))}, 2 );
  TEST_NULL( {type.view(t, s("date"))} );
""")

x.unit(f"{type.range}(): traverse in lexicographical key order", f"""
  {type.create(t)};
  {type.set(t, s("cherry"), 3)};
  {type.set(t, s("apple"), 1)};
  {type.set(t, s("banana"), 2)};
  {{
    int values[3];
    int count = 0;
    {r.definition};
    for({r} = {range.new(t)}; !{range.empty(r)}; {range.move_front(r)}) {{
      values[count++] = {range.front(r)};
    }}
    TEST_EQUAL( count, 3 );
    TEST_EQUAL( values[0], 1 ); /* apple */
    TEST_EQUAL( values[1], 2 ); /* banana */
    TEST_EQUAL( values[2], 3 ); /* cherry */
  }}
""")

x.unit(f"{type.copy}/{type.equal}(): copy and equality with string keys", f"""
  {type.create(t)};
  {type.set(t, s("apple"), 1)};
  {type.set(t, s("banana"), 2)};
  {{
    {type.variable("other").definition};
    {type.copy("&other", t)};
    TEST_EQUAL( {type.size("&other")}, 2 );
    TEST_TRUE( {type.equal(t, "&other")} );
    {type.set("&other", s("cherry"), 3)};
    TEST_FALSE( {type.equal(t, "&other")} );
    {type.destroy("&other")};
  }}
""")
