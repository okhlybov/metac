from metac.test import *
from metac.flat_multimap import Map

x = Type(type := Map("flat_int2int_multimap", "int", "int"))

t = type.variable("t")

range = type.range
r = range.variable("r")

x.setup(f"""
  {t.definition};
""")
x.cleanup(f"""
  {type.destroy(t)};
""")

x.unit(f"{type.create}(): create empty multimap", f"""
  {type.create(t)};
  TEST_TRUE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 0 );
  TEST_EQUAL( {type.capacity(t)}, 0 );
""")

x.unit(f"{type.put}(): put into multimap preserving duplicates", f"""
  {type.create(t)};
  TEST_EQUAL( {type.put(t, 10, 100)}, 1 );
  TEST_FALSE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 1 );
  TEST_TRUE( {type.capacity(t)} >= 1 );
  TEST_EQUAL( {type.get(t, 10)}, 100 );

  /* Insert duplicate keys */
  TEST_EQUAL( {type.put(t, 10, 200)}, 1 );
  TEST_EQUAL( {type.put(t, 10, 300)}, 1 );
  TEST_EQUAL( {type.size(t)}, 3 );
  TEST_EQUAL( {type.count(t, 10)}, 3 );
  /* First inserted element is returned by get/view */
  TEST_EQUAL( {type.get(t, 10)}, 100 );
""")

x.unit(f"{type.reserve}/{type.compact}(): reserve and compact multimap", f"""
  {type.create(t)};
  {type.reserve(t, 50)};
  TEST_TRUE( {type.capacity(t)} >= 50 );
  {type.put(t, 1, 10)};
  {type.put(t, 1, 20)};
  {type.put(t, 2, 30)};
  {type.compact(t)};
  TEST_EQUAL( {type.size(t)}, 3 );
  TEST_EQUAL( {type.capacity(t)}, 3 );
""")

x.unit(f"{type.indexed}(): indexed check", f"""
  {type.create(t)};
  TEST_FALSE( {type.indexed(t, 10)} );
  {type.put(t, 10, 1)};
  {type.put(t, 10, 2)};
  {type.put(t, 30, 3)};
  {type.put(t, 20, 4)};
  TEST_TRUE( {type.indexed(t, 10)} );
  TEST_TRUE( {type.indexed(t, 20)} );
  TEST_TRUE( {type.indexed(t, 30)} );
  TEST_FALSE( {type.indexed(t, 15)} );
""")

x.unit(f"{type.count}(): count occurrences of key", f"""
  {type.create(t)};
  TEST_EQUAL( {type.count(t, 10)}, 0 );
  {type.put(t, 10, 1)};
  {type.put(t, 20, 2)};
  {type.put(t, 20, 3)};
  {type.put(t, 20, 4)};
  {type.put(t, 30, 5)};
  TEST_EQUAL( {type.count(t, 10)}, 1 );
  TEST_EQUAL( {type.count(t, 20)}, 3 );
  TEST_EQUAL( {type.count(t, 30)}, 1 );
  TEST_EQUAL( {type.count(t, 99)}, 0 );
""")

x.unit(f"{type.view}(): view of existing and absent", f"""
  {type.create(t)};
  TEST_NULL( {type.view(t, 10)} );
  {type.put(t, 10, 42)};
  {type.put(t, 10, 99)};
  TEST_NOT_NULL( {type.view(t, 10)} );
  TEST_EQUAL( *{type.view(t, 10)}, 42 );
  TEST_NULL( {type.view(t, 99)} );
""")

x.unit(f"{type.contains}(): contains mapped value", f"""
  {type.create(t)};
  TEST_FALSE( {type.contains(t, 42)} );
  {type.put(t, 10, 42)};
  {type.put(t, 20, 84)};
  TEST_TRUE( {type.contains(t, 42)} );
  TEST_TRUE( {type.contains(t, 84)} );
  TEST_FALSE( {type.contains(t, 99)} );
""")

x.unit(f"{type.remove}(): remove single entry with key", f"""
  {type.create(t)};
  {type.put(t, 10, 100)};
  {type.put(t, 20, 200)};
  {type.put(t, 20, 201)};
  {type.put(t, 30, 300)};
  TEST_EQUAL( {type.size(t)}, 4 );

  TEST_FALSE( {type.remove(t, 99)} );
  TEST_EQUAL( {type.size(t)}, 4 );

  /* Remove one of the 20s (the first one) */
  TEST_TRUE( {type.remove(t, 20)} );
  TEST_EQUAL( {type.size(t)}, 3 );
  TEST_EQUAL( {type.count(t, 20)}, 1 );
  TEST_EQUAL( {type.get(t, 20)}, 201 );

  /* Remove the remaining 20 */
  TEST_TRUE( {type.remove(t, 20)} );
  TEST_EQUAL( {type.size(t)}, 2 );
  TEST_EQUAL( {type.count(t, 20)}, 0 );
  TEST_FALSE( {type.indexed(t, 20)} );

  TEST_FALSE( {type.remove(t, 20)} );
  TEST_EQUAL( {type.size(t)}, 2 );
""")

x.unit(f"{type.wipe}(): wipe all entries with key", f"""
  {type.create(t)};
  {type.put(t, 10, 100)};
  {type.put(t, 10, 101)};
  {type.put(t, 20, 200)};
  {type.put(t, 20, 201)};
  {type.put(t, 20, 202)};
  {type.put(t, 30, 300)};
  TEST_EQUAL( {type.size(t)}, 6 );

  /* Absent key */
  TEST_EQUAL( {type.wipe(t, 99)}, 0 );
  TEST_EQUAL( {type.size(t)}, 6 );

  /* Wipe middle: three 20s */
  TEST_EQUAL( {type.wipe(t, 20)}, 3 );
  TEST_EQUAL( {type.size(t)}, 3 );
  TEST_EQUAL( {type.count(t, 20)}, 0 );
  TEST_FALSE( {type.indexed(t, 20)} );

  /* Wipe first: two 10s */
  TEST_EQUAL( {type.wipe(t, 10)}, 2 );
  TEST_EQUAL( {type.size(t)}, 1 );
  TEST_EQUAL( {type.count(t, 10)}, 0 );

  /* Wipe last remaining: one 30 */
  TEST_EQUAL( {type.wipe(t, 30)}, 1 );
  TEST_TRUE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 0 );
""")

x.unit(f"{type.equal_range}(): get range spanning all entries with key", f"""
  {type.create(t)};
  {type.put(t, 10, 100)};
  {type.put(t, 20, 200)};
  {type.put(t, 20, 201)};
  {type.put(t, 20, 202)};
  {type.put(t, 30, 300)};

  {{
    int values[3];
    int count = 0;
    {range} eq = {type.equal_range(t, 20)};
    TEST_FALSE( {range.empty("&eq")} );
    TEST_EQUAL( {range.size("&eq")}, 3 );
    while(!{range.empty("&eq")}) {{
      TEST_EQUAL( {range.index_front("&eq")}, 20 );
      values[count++] = {range.front("&eq")};
      {range.move_front("&eq")};
    }}
    TEST_EQUAL( count, 3 );
    TEST_EQUAL( values[0], 200 );
    TEST_EQUAL( values[1], 201 );
    TEST_EQUAL( values[2], 202 );
  }}

  {{
    {range} eq = {type.equal_range(t, 99)};
    TEST_TRUE( {range.empty("&eq")} );
    TEST_EQUAL( {range.size("&eq")}, 0 );
  }}
""")

x.unit(f"{type.range}(): traverse in sorted key order with FIFO duplicates", f"""
  {type.create(t)};
  {type.put(t, 30, 300)};
  {type.put(t, 10, 100)};
  {type.put(t, 20, 200)};
  {type.put(t, 20, 201)};
  {type.put(t, 10, 101)};
  {{
    int keys[5];
    int values[5];
    int count = 0;
    {r.definition};
    for({r} = {range.new(t)}; !{range.empty(r)}; {range.move_front(r)}) {{
      keys[count] = {range.index_front(r)};
      values[count] = {range.front(r)};
      ++count;
    }}
    TEST_EQUAL( count, 5 );
    /* Keys in ascending order, duplicate keys in FIFO order */
    TEST_EQUAL( keys[0], 10 );
    TEST_EQUAL( values[0], 100 );
    TEST_EQUAL( keys[1], 10 );
    TEST_EQUAL( values[1], 101 );
    TEST_EQUAL( keys[2], 20 );
    TEST_EQUAL( values[2], 200 );
    TEST_EQUAL( keys[3], 20 );
    TEST_EQUAL( values[3], 201 );
    TEST_EQUAL( keys[4], 30 );
    TEST_EQUAL( values[4], 300 );
  }}
""")

x.unit(f"{type.copy}/{type.equal}/{type.compare}(): copy, equality, ordering", f"""
  {type.create(t)};
  {type.put(t, 1, 10)};
  {type.put(t, 1, 20)};
  {type.put(t, 2, 30)};
  {{
    {type.variable("other").definition};
    {type.create("&other")};
    {type.copy("&other", t)};
    TEST_EQUAL( {type.size("&other")}, 3 );
    TEST_TRUE( {type.equal(t, "&other")} );
    TEST_EQUAL( {type.compare(t, "&other")}, 0 );
    TEST_EQUAL( {type.hash(t)}, {type.hash("&other")} );

    /* Adding another duplicate breaks equality */
    {type.put("&other", 1, 99)};
    TEST_FALSE( {type.equal(t, "&other")} );
    {type.destroy("&other")};
  }}
""")
