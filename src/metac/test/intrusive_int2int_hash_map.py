from metac.test import *
from metac.intrusive_hash_map import Map

# Better to use index field for marking entries otherwise
# memory debuggers gonna complain about uninitialized access

states = {
  "empty": (
    lambda entry: f"{entry}.index == INT_MIN /* empty? */",
    lambda entry: f"{entry}.index = INT_MIN /* empty! */",
  ),
  "deleted": (
    lambda entry: f"{entry}.index == INT_MAX /* deleted? */",
    lambda entry: f"{entry}.index = INT_MAX /* deleted! */",
  ),
}

x = Type(type := Map("intrusive_int2int_hash_map", "int", "int", states))

t = type.variable("t")

range = type.range
r = range.variable("r")

x.setup(f"""
  {t.definition};
""")
x.cleanup(f"""
  {type.destroy(t)};
""")

x.unit(f"{type.create}(): create empty set with zero size", f"""
  {type.create(t)};
  TEST_TRUE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 0 );
""")

x.unit(f"{type.create}(): put to empty map", f"""
  {type.create(t)};
  TEST_TRUE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 0 );
  {type.set(t, 0, 0)};
  TEST_FALSE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 1 );
""")

x.unit(f"{type.create}(): put to !empty map", f"""
  {type.create(t)};
  TEST_TRUE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 0 );
  {type.set(t, 0, 0)};
  {type.set(t, 1, -1)};
  TEST_FALSE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 2 );
""")

x.setup(f"""
  int i;
  {t.definition};
  {r.definition};
  {type.create(t)};
""")

x.unit(f"{type.range}(): traverse empty map", f"""
  {r} = {range.new(t)};
  TEST_TRUE( {range.empty(r)} );
""")

x.unit(f"{type.range}(): traverse map", f"""
  for(i = 0; i < 16; ++i) {type.set(t, "i", "-i")};
  TEST_EQUAL( {type.size(t)}, 16 );
  {{
    int mask = 0;
    for({r} = {range.new(t)}; !{range.empty(r)}; {range.move_front(r)}) {{
      TEST_EQUAL( *{range.front_view(r)}, -*{range.index_front_view(r)} );
      mask |= 1 << *{range.index_front_view(r)};
    }}
    TEST_EQUAL( mask, 0xFFFF );
  }}
""")

x.unit(f"{type.range}(): front of map range", f"""
  {type.set(t, 42, -42)};
  {r} = {range.new(t)};
  TEST_FALSE( {range.empty(r)} );
  TEST_EQUAL( {range.index_front(r)}, 42 );
  TEST_EQUAL( {range.front(r)}, -42 );
  {range.move_front(r)};
  TEST_TRUE( {range.empty(r)} );
""")

x.unit(f"{type.get}(): get from map", f"""
  {type.set(t, 42, -42)};
  TEST_EQUAL( {type.get(t, 42)}, -42 );
""")

x.unit(f"{type.range}(): traverse empty map", f"""
  {type.destroy(t)};
  {type.create(t)};
  {r} = {range.new(t)};
  TEST_TRUE( {range.empty(r)} );
""")