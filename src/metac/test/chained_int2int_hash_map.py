from metac.test import *
from metac.chained_hash_map import Map

x = Type(type := Map("chained_int2int_hash_map", "int", "int"))

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
  TEST_TRUE( {type.empty(t)} );
  {type.set(t, 0, 0)};
  TEST_FALSE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 1 );
""")

x.unit(f"{type.set}(): set into !empty map", f"""
  {type.create(t)};
  {type.set(t, 0, 0)};
  {type.set(t, 1, -1)};
  TEST_FALSE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 2 );
""")

x.unit(f"{type.set}(): overwrite existing entry", f"""
  {type.create(t)};
  {type.set(t, 0, 0)};
  {type.set(t, 0, 1)};
  TEST_EQUAL( {type.size(t)}, 1 );
  TEST_EQUAL( {type.get(t, 0)}, 1 );
""")

x.unit(f"{type.contains}(): !contained element in empty map", f"""
  {type.create(t)};
  TEST_FALSE( {type.contains(t, 0)} );
""")

x.unit(f"{type.indexed}(): !indexed in empty map", f"""
  {type.create(t)};
  TEST_FALSE( {type.indexed(t, 0)} );
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

x.unit(f"{type.contains}(): contained element in !empty map", f"""
  TEST_TRUE( {type.contains(t, 0)} );
""")

x.unit(f"{type.contains}(): !contained element in !empty map", f"""
  TEST_FALSE( {type.contains(t, -1)} );
""")

x.unit(f"{type.indexed}(): indexed in !empty map", f"""
  TEST_TRUE( {type.indexed(t, 0)} );
""")

x.unit(f"{type.indexed}(): !indexed in !empty map", f"""
  TEST_FALSE( {type.indexed(t, -1)} );
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

x.unit(f"{range}(): traverse empty map", f"""
  {r} = {range.new(t)};
  TEST_TRUE( {range.empty(r)} );
""")

x.unit(f"{range}(): traverse map", f"""
  for(i = 0; i < 16; ++i) {type.set(t, "i", "-i")};
  TEST_EQUAL( {type.size(t)}, 16 );
  {{
    unsigned mask = 0;
    for({r} = {range.new(t)}; !{range.empty(r)}; {range.move_front(r)}) {{
      TEST_EQUAL( *{range.front_view(r)}, -*{range.index_front_view(r)} );
      mask |= 1 << *{range.index_front_view(r)};
    }}
    TEST_EQUAL( mask, 0xFFFF );
  }}
""")

x.unit(f"{range}(): front of map range", f"""
  {type.set(t, 42, -42)};
  {r} = {range.new(t)};
  TEST_FALSE( {range.empty(r)} );
  TEST_EQUAL( {range.index_front(r)}, 42 );
  TEST_EQUAL( {range.front(r)}, -42 );
  {range.move_front(r)};
  TEST_TRUE( {range.empty(r)} );
""")

x.unit(f"{type.copy}(): copy map", f"""
  {type.variable("t2").definition};
  {type.create(type.variable("t2"))};
  for(i = 0; i < 8; ++i) {type.set(t, "i", "-i")};
  {type.copy(type.variable("t2"), t)};
  TEST_TRUE( {type.equal(t, type.variable("t2"))} );
  TEST_EQUAL( {type.hash(t)}, {type.hash(type.variable("t2"))} );
  TEST_EQUAL( {type.size(type.variable("t2"))}, 8 );
  TEST_EQUAL( {type.get(type.variable("t2"), 7)}, -7 );
  {type.destroy(type.variable("t2"))};
""")
