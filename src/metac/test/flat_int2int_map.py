from metac.test import *
from metac.flat_map import Map

x = Type(type := Map("flat_int2int_map", "int", "int"))

t = type.variable("t")

range = type.range
r = range.variable("r")

x.setup(f"""
  {t.definition};
""")
x.cleanup(f"""
  {type.destroy(t)};
""")

x.unit(f"{type.create}(): create empty map", f"""
  {type.create(t)};
  TEST_TRUE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 0 );
  TEST_EQUAL( {type.capacity(t)}, 0 );
""")

x.unit(f"{type.set}(): set into empty map", f"""
  {type.create(t)};
  {type.set(t, 0, 100)};
  TEST_FALSE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 1 );
  TEST_TRUE( {type.capacity(t)} >= 1 );
  TEST_EQUAL( {type.get(t, 0)}, 100 );
""")

x.unit(f"{type.set}(): overwrite existing entry", f"""
  {type.create(t)};
  {type.set(t, 0, 100)};
  {type.set(t, 0, 200)};
  TEST_EQUAL( {type.size(t)}, 1 );
  TEST_EQUAL( {type.get(t, 0)}, 200 );
""")

x.unit(f"{type.reserve}/{type.compact}(): reserve and compact map", f"""
  {type.create(t)};
  {type.reserve(t, 50)};
  TEST_TRUE( {type.capacity(t)} >= 50 );
  {type.set(t, 1, 10)};
  {type.set(t, 2, 20)};
  {type.compact(t)};
  TEST_EQUAL( {type.size(t)}, 2 );
  TEST_EQUAL( {type.capacity(t)}, 2 );
""")

x.unit(f"{type.indexed}(): indexed check", f"""
  {type.create(t)};
  TEST_FALSE( {type.indexed(t, 10)} );
  {type.set(t, 10, 1)};
  {type.set(t, 30, 3)};
  {type.set(t, 20, 2)};
  TEST_TRUE( {type.indexed(t, 10)} );
  TEST_TRUE( {type.indexed(t, 20)} );
  TEST_TRUE( {type.indexed(t, 30)} );
  TEST_FALSE( {type.indexed(t, 15)} );
""")

x.unit(f"{type.remove}(): remove key from map", f"""
  {type.create(t)};
  {type.set(t, 10, 100)};
  {type.set(t, 20, 200)};
  TEST_EQUAL( {type.size(t)}, 2 );
  TEST_TRUE( {type.remove(t, 10)} );
  TEST_EQUAL( {type.size(t)}, 1 );
  TEST_FALSE( {type.indexed(t, 10)} );
  TEST_TRUE( {type.indexed(t, 20)} );
  TEST_FALSE( {type.remove(t, 10)} );
  TEST_EQUAL( {type.size(t)}, 1 );
  TEST_TRUE( {type.remove(t, 20)} );
  TEST_TRUE( {type.empty(t)} );
""")

x.unit(f"{type.view}(): view of existing and absent", f"""
  {type.create(t)};
  TEST_NULL( {type.view(t, 10)} );
  {type.set(t, 10, 42)};
  TEST_NOT_NULL( {type.view(t, 10)} );
  TEST_EQUAL( *{type.view(t, 10)}, 42 );
  TEST_NULL( {type.view(t, 99)} );
""")

x.unit(f"{type.contains}(): contains mapped value", f"""
  {type.create(t)};
  TEST_FALSE( {type.contains(t, 42)} );
  {type.set(t, 10, 42)};
  TEST_TRUE( {type.contains(t, 42)} );
  TEST_FALSE( {type.contains(t, 99)} );
""")

x.unit(f"{type.range}(): traverse in sorted key order", f"""
  {type.create(t)};
  {type.set(t, 30, 300)};
  {type.set(t, 10, 100)};
  {type.set(t, 20, 200)};
  {{
    int keys[3];
    int values[3];
    int count = 0;
    {r.definition};
    for({r} = {range.new(t)}; !{range.empty(r)}; {range.move_front(r)}) {{
      keys[count] = {range.index_front(r)};
      values[count] = {range.front(r)};
      ++count;
    }}
    TEST_EQUAL( count, 3 );
    TEST_EQUAL( keys[0], 10 );
    TEST_EQUAL( values[0], 100 );
    TEST_EQUAL( keys[1], 20 );
    TEST_EQUAL( values[1], 200 );
    TEST_EQUAL( keys[2], 30 );
    TEST_EQUAL( values[2], 300 );
  }}
""")

x.unit(f"{type.range}(): traverse in descending key order", f"""
  {type.create(t)};
  {type.set(t, 30, 300)};
  {type.set(t, 10, 100)};
  {type.set(t, 20, 200)};
  {{
    int keys[3];
    int values[3];
    int count = 0;
    {r.definition};
    for({r} = {range.new(t)}; !{range.empty(r)}; {range.move_back(r)}) {{
      keys[count] = {range.index_back(r)};
      values[count] = {range.back(r)};
      ++count;
    }}
    TEST_EQUAL( count, 3 );
    TEST_EQUAL( keys[0], 30 );
    TEST_EQUAL( values[0], 300 );
    TEST_EQUAL( keys[1], 20 );
    TEST_EQUAL( values[1], 200 );
    TEST_EQUAL( keys[2], 10 );
    TEST_EQUAL( values[2], 100 );
  }}
""")

x.unit(f"{type.copy}/{type.equal}/{type.compare}(): copy, equality, ordering", f"""
  {type.create(t)};
  {type.set(t, 1, 10)};
  {type.set(t, 2, 20)};
  {{
    {type.variable("other").definition};
    {type.copy("&other", t)};
    TEST_EQUAL( {type.size("&other")}, 2 );
    TEST_TRUE( {type.equal(t, "&other")} );
    TEST_EQUAL( {type.compare(t, "&other")}, 0 );
    {type.set("&other", 3, 30)};
    TEST_FALSE( {type.equal(t, "&other")} );
    TEST_TRUE( {type.compare(t, "&other")} < 0 );
    {type.destroy("&other")};
  }}
""")

k_expr = "(i * 37) % 50"
v_expr = "i * 10"

x.unit("multi-element insertion: range yields strictly ascending keys", f"""
  int i;
  int prev_k = -1;
  {type.create(t)};
  for(i = 0; i < 50; ++i) {{
    {type.set(t, k_expr, v_expr)};
  }}
  TEST_EQUAL( {type.size(t)}, 50 );
  {{
    {r.definition};
    for({r} = {range.new(t)}; !{range.empty(r)}; {range.move_front(r)}) {{
      int k = {range.index_front(r)};
      TEST_TRUE( k > prev_k );
      prev_k = k;
    }}
  }}
""")

