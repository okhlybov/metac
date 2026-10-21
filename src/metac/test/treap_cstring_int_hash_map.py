from metac.test import *
from metac.tree_map import Map
from metac.treap_set import Set as TreapSet
from metac.test.cstring import cstring, s

# Hash map keyed by a composite (string) index over the treap - the entries are
# ordered by the string keys and iterated in the lexicographical order

x = Type(type := Map("treap_cstring_int_hash_map", "int", cstring, TreapSet))

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
  {type.set(t, s("one"), 1)};
  TEST_FALSE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 1 );
""")

x.unit(f"{type.set}(): overwrite existing entry", f"""
  {type.create(t)};
  {type.set(t, s("one"), 1)};
  {type.set(t, s("one"), 2)};
  TEST_EQUAL( {type.size(t)}, 1 );
  TEST_EQUAL( {type.get(t, s("one"))}, 2 );
""")

x.unit(f"{type.indexed}(): !indexed in empty map", f"""
  {type.create(t)};
  TEST_FALSE( {type.indexed(t, s("one"))} );
""")


x.setup(f"""
  {t.definition};
  {type.create(t)};
  {type.set(t, s("one"), 1)};
  {type.set(t, s("two"), 2)};
""")
x.cleanup(f"""
  {type.destroy(t)};
""")

x.unit(f"{type.contains}(): contained element in !empty map", f"""
  TEST_TRUE( {type.contains(t, 1)} );
  TEST_FALSE( {type.contains(t, 3)} );
""")

x.unit(f"{type.indexed}(): indexed in !empty map", f"""
  TEST_TRUE( {type.indexed(t, s("one"))} );
  TEST_FALSE( {type.indexed(t, s("One"))} );
""")

x.unit(f"{type.view}(): view of existing entry", f"""
  TEST_EQUAL( *{type.view(t, s("two"))}, 2 );
""")

x.unit(f"{type.view}(): view of !existing entry", f"""
  TEST_TRUE( {type.view(t, s("three"))} == NULL );
""")

x.unit(f"{type.get}(): get from map", f"""
  TEST_EQUAL( {type.get(t, s("one"))}, 1 );
  TEST_EQUAL( {type.get(t, s("two"))}, 2 );
""")

x.unit(f"{type.hash}(): hash !empty map", f"""
  {type.hash(t)};
""")

x.unit(f"{type.equal}(): compare maps with string keys", f"""
  {type.variable("t2").definition};
  {type.create(type.variable("t2"))};
  {type.set(type.variable("t2"), s("one"), 1)};
  {type.set(type.variable("t2"), s("two"), 2)};
  TEST_TRUE( {type.equal(t, type.variable("t2"))} );
  {type.set(type.variable("t2"), s("three"), 3)};
  TEST_FALSE( {type.equal(t, type.variable("t2"))} );
  {type.destroy(type.variable("t2"))};
""")


x.setup(f"""
  {t.definition};
  {r.definition};
  {type.create(t)};
""")
x.cleanup(f"""
  {type.destroy(t)};
""")

x.unit(f"{range}(): traverse the map in the lexicographical order", f"""
  {type.set(t, s("pear"), 3)};
  {type.set(t, s("apple"), 1)};
  {type.set(t, s("orange"), 2)};
  {type.set(t, s("banana"), 4)};
  {{
    const char* expected_keys[] = {{"apple", "banana", "orange", "pear"}};
    int expected_values[] = {{1, 4, 2, 3}};
    int i = 0;
    for({r} = {range.new(t)}; !{range.empty(r)}; {range.move_front(r)}) {{
      TEST_EQUAL_CHARS( {range.index_front_view(r)}, expected_keys[i] );
      TEST_EQUAL( {range.front(r)}, expected_values[i] );
      ++i;
    }}
    TEST_EQUAL( i, 4 );
  }}
""")
