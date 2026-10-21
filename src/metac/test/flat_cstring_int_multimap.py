from metac.test import *
from metac.flat_multimap import Map
from metac.test.cstring import cstring, s

x = Type(type := Map("flat_cstring_int_multimap", "int", cstring))

t = type.variable("t")

range = type.range
r = range.variable("r")

x.setup(f"""
  {t.definition};
""")
x.cleanup(f"""
  {type.destroy(t)};
""")

x.unit(f"{type.put}(): put into multimap with string keys", f"""
  {type.create(t)};
  TEST_TRUE( {type.empty(t)} );
  TEST_EQUAL( {type.put(t, s("apple"), 1)}, 1 );
  TEST_FALSE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 1 );
  TEST_EQUAL( {type.get(t, s("apple"))}, 1 );

  /* Put duplicate string key */
  TEST_EQUAL( {type.put(t, s("apple"), 10)}, 1 );
  TEST_EQUAL( {type.size(t)}, 2 );
  TEST_EQUAL( {type.count(t, s("apple"))}, 2 );
  TEST_EQUAL( {type.get(t, s("apple"))}, 1 );
""")

x.unit(f"{type.indexed}(): indexed and view lookup", f"""
  {type.create(t)};
  {type.put(t, s("cherry"), 3)};
  {type.put(t, s("apple"), 1)};
  {type.put(t, s("banana"), 2)};
  {type.put(t, s("banana"), 20)};
  TEST_TRUE( {type.indexed(t, s("apple"))} );
  TEST_TRUE( {type.indexed(t, s("banana"))} );
  TEST_TRUE( {type.indexed(t, s("cherry"))} );
  TEST_FALSE( {type.indexed(t, s("date"))} );
  TEST_NOT_NULL( {type.view(t, s("banana"))} );
  TEST_EQUAL( *{type.view(t, s("banana"))}, 2 );
  TEST_NULL( {type.view(t, s("date"))} );
""")

x.unit(f"{type.equal_range}(): equal_range with string keys", f"""
  {type.create(t)};
  {type.put(t, s("apple"), 1)};
  {type.put(t, s("banana"), 20)};
  {type.put(t, s("banana"), 21)};
  {type.put(t, s("cherry"), 3)};
  {{
    int values[2];
    int count = 0;
    {range} eq = {type.equal_range(t, s("banana"))};
    TEST_FALSE( {range.empty("&eq")} );
    TEST_EQUAL( {range.size("&eq")}, 2 );
    while(!{range.empty("&eq")}) {{
      values[count++] = {range.front("&eq")};
      {range.move_front("&eq")};
    }}
    TEST_EQUAL( count, 2 );
    TEST_EQUAL( values[0], 20 );
    TEST_EQUAL( values[1], 21 );
  }}
""")

x.unit(f"{type.wipe}(): wipe with string keys", f"""
  {type.create(t)};
  {type.put(t, s("apple"), 1)};
  {type.put(t, s("banana"), 20)};
  {type.put(t, s("banana"), 21)};
  {type.put(t, s("cherry"), 3)};
  TEST_EQUAL( {type.size(t)}, 4 );

  TEST_EQUAL( {type.wipe(t, s("banana"))}, 2 );
  TEST_EQUAL( {type.size(t)}, 2 );
  TEST_FALSE( {type.indexed(t, s("banana"))} );
  TEST_TRUE( {type.indexed(t, s("apple"))} );
  TEST_TRUE( {type.indexed(t, s("cherry"))} );
""")

x.unit(f"{type.range}(): traverse in lexicographical key order", f"""
  {type.create(t)};
  {type.put(t, s("cherry"), 3)};
  {type.put(t, s("apple"), 1)};
  {type.put(t, s("banana"), 2)};
  {type.put(t, s("banana"), 20)};
  {{
    int values[4];
    int count = 0;
    {r.definition};
    for({r} = {range.new(t)}; !{range.empty(r)}; {range.move_front(r)}) {{
      values[count++] = {range.front(r)};
    }}
    TEST_EQUAL( count, 4 );
    TEST_EQUAL( values[0], 1 );  /* apple */
    TEST_EQUAL( values[1], 2 );  /* banana #1 */
    TEST_EQUAL( values[2], 20 ); /* banana #2 */
    TEST_EQUAL( values[3], 3 );  /* cherry */
  }}
""")

x.unit(f"{type.copy}/{type.equal}(): copy and equality with string keys", f"""
  {type.create(t)};
  {type.put(t, s("apple"), 1)};
  {type.put(t, s("banana"), 2)};
  {{
    {type.variable("other").definition};
    {type.create("&other")};
    {type.copy("&other", t)};
    TEST_EQUAL( {type.size("&other")}, 2 );
    TEST_TRUE( {type.equal(t, "&other")} );
    {type.put("&other", s("cherry"), 3)};
    TEST_FALSE( {type.equal(t, "&other")} );
    {type.destroy("&other")};
  }}
""")
