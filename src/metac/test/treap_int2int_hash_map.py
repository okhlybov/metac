from metac.test import *
from metac.tree_map import Map
from metac.treap_set import Set as TreapSet

x = Type(type := Map("treap_int2int_hash_map", "int", "int", TreapSet))

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
""")

x.unit(f"{type.set}(): set into empty map", f"""
  {type.create(t)};
  {type.set(t, 0, 0)};
  TEST_FALSE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 1 );
""")

x.unit(f"{type.set}(): overwrite existing entry", f"""
  {type.create(t)};
  {type.set(t, 0, 0)};
  {type.set(t, 0, 1)};
  TEST_EQUAL( {type.size(t)}, 1 );
  TEST_EQUAL( {type.get(t, 0)}, 1 );
""")

x.unit(f"{type.indexed}(): !indexed in empty map", f"""
  {type.create(t)};
  TEST_FALSE( {type.indexed(t, 0)} );
""")

x.unit(f"{type.contains}(): !contained element in empty map", f"""
  {type.create(t)};
  TEST_FALSE( {type.contains(t, 0)} );
""")

x.unit(f"{type.hash}(): hash empty map", f"""
  {type.create(t)};
  {type.hash(t)};
""")


x.setup(f"""
  {t.definition};
  {type.create(t)};
  {type.set(t, 0, 0)};
""")
x.cleanup(f"""
  {type.destroy(t)};
""")

x.unit(f"{type.indexed}(): indexed in !empty map", f"""
  TEST_TRUE( {type.indexed(t, 0)} );
  TEST_FALSE( {type.indexed(t, -1)} );
""")

x.unit(f"{type.contains}(): contained element in !empty map", f"""
  TEST_TRUE( {type.contains(t, 0)} );
  TEST_FALSE( {type.contains(t, -1)} );
""")

x.unit(f"{type.view}(): view of existing entry", f"""
  TEST_EQUAL( *{type.view(t, 0)}, 0 );
""")

x.unit(f"{type.view}(): view of !existing entry", f"""
  TEST_TRUE( {type.view(t, -1)} == NULL );
""")

x.unit(f"{type.get}(): get from map", f"""
  TEST_EQUAL( {type.get(t, 0)}, 0 );
""")

x.unit(f"{type.hash}(): hash !empty map", f"""
  {type.hash(t)};
""")


x.setup(f"""
  int i;
  {t.definition};
  {r.definition};
  {type.create(t)};
""")
x.cleanup(f"""
  {type.destroy(t)};
""")

x.unit(f"{type.set}(): fill the map", f"""
  for(i = 0; i < 32; ++i) {type.set(t, "(i*7%32)", "-(i*7%32)")};
  TEST_EQUAL( {type.size(t)}, 32 );
""")

x.unit(f"{type.get}(): get all entries", f"""
  for(i = 0; i < 32; ++i) {type.set(t, "(i*7%32)", "-(i*7%32)")};
  for(i = 0; i < 32; ++i) TEST_EQUAL( {type.get(t, "(i*7%32)")}, -(i*7%32) );
""")

x.unit(f"{range}(): traverse the map in the index order", f"""
  for(i = 0; i < 32; ++i) {type.set(t, "(i*7%32)", "-(i*7%32)")};
  {{
    int previous = -1;
    int count = 0;
    for({r} = {range.new(t)}; !{range.empty(r)}; {range.move_front(r)}) {{
      int index = {range.index_front(r)};
      TEST_TRUE( index > previous );
      previous = index;
      TEST_EQUAL( {range.front(r)}, -index );
      ++count;
    }}
    TEST_EQUAL( count, 32 );
  }}
""")

x.unit(f"{type.copy}(): copy the map", f"""
  {type.variable("t2").definition};
  {type.create(type.variable("t2"))};
  for(i = 0; i < 16; ++i) {type.set(t, "i", "-i")};
  {type.copy(type.variable("t2"), t)};
  TEST_TRUE( {type.equal(t, type.variable("t2"))} );
  TEST_EQUAL( {type.hash(t)}, {type.hash(type.variable("t2"))} );
  TEST_EQUAL( {type.size(type.variable("t2"))}, 16 );
  TEST_EQUAL( {type.get(type.variable("t2"), 15)}, -15 );
  {type.destroy(type.variable("t2"))};
""")

x.unit(f"{type.equal}(): compare maps holding different indices", f"""
  {type.variable("t2").definition};
  {type.create(type.variable("t2"))};
  for(i = 0; i < 8; ++i) {type.set(t, "i", "-i")};
  for(i = 0; i < 8; ++i) {type.set(type.variable("t2"), "i + 1", "-i")};
  TEST_FALSE( {type.equal(t, type.variable("t2"))} );
  {type.destroy(type.variable("t2"))};
""")

x.unit(f"{type.compare}(): order maps by their indices", f"""
  {type.variable("t2").definition};
  {type.create(type.variable("t2"))};
  {type.set(t, 1, -1)};
  {type.set(t, 3, -3)};
  {type.set(type.variable("t2"), 1, -1)};
  {type.set(type.variable("t2"), 3, -3)};
  TEST_EQUAL( {type.compare(t, type.variable("t2"))}, 0 );
  {type.set(type.variable("t2"), 5, -5)};
  TEST_TRUE( {type.compare(t, type.variable("t2"))} < 0 );
  {type.destroy(type.variable("t2"))};
""")
