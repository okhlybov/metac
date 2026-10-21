from metac.test import *
from metac.btree_map import Map

x = Type(type := Map("btree_int2int_map", "int", "int", order=4))

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

x.unit(f"{type.view}(): view existing element", f"""
  TEST_EQUAL( *{type.view(t, 0)}, 0 );
""")

x.unit(f"{type.indexed}(): indexed in !empty map", f"""
  TEST_TRUE( {type.indexed(t, 0)} );
""")

x.unit(f"{type.contains}(): contained element in !empty map", f"""
  TEST_TRUE( {type.contains(t, 0)} );
""")

x.unit(f"{type.indexed}(): !indexed in !empty map", f"""
  TEST_FALSE( {type.indexed(t, -1)} );
""")

x.unit(f"{type.contains}(): !contained element in !empty map", f"""
  TEST_FALSE( {type.contains(t, -1)} );
""")

x.unit(f"{type.hash}(): hash !empty map", f"""
  {type.hash(t)};
""")

x.unit(f"{type.set}/{type.remove}: removal keeps the map consistent", f"""
  int i;
  for(i = 1; i < 32; ++i) {{ {type.set(t, "i", "i")}; }}
  TEST_EQUAL( {type.size(t)}, 32 );
  for(i = 0; i < 32; ++i) {{
    TEST_TRUE( {type.remove(t, "i")} );
    TEST_EQUAL( {type.size(t)}, 31-i );
    TEST_FALSE( {type.indexed(t, "i")} );
  }}
  TEST_TRUE( {type.empty(t)} );
""")


x.setup(f"""
  int i;
  {r.definition};
  {t.definition};
  {type.create(t)};
""")
x.cleanup(f"""
  {type.destroy(t)};
""")

x.unit(f"{range}(): traverse empty map", f"""
  {r} = {range.new(t)};
  TEST_TRUE( {range.empty(r)} );
""")

x.unit(f"{range}(): traverse !empty map", f"""
  unsigned mask = 0;
  for(i = 0; i < 32; ++i) {type.set(t, "i", "i")};
  TEST_EQUAL( {type.size(t)}, 32 );
  for({r} = {range.new(t)}; !{range.empty(r)}; {range.move_front(r)}) {{
    mask |= 1 << {range.front(r)};
  }}
  TEST_EQUAL( mask, 0xFFFFFFFF );
""")

x.unit(f"{range}(): traverse in ascending key order", f"""
  int previous;
  for(i = 0; i < 32; ++i) {type.set(t, "(i*7)%32", "i")};
  TEST_EQUAL( {type.size(t)}, 32 );
  previous = -1;
  for({r} = {range.new(t)}; !{range.empty(r)}; {range.move_front(r)}) {{
    TEST_TRUE( *{range.index_front_view(r)} > previous );
    previous = *{range.index_front_view(r)};
  }}
  TEST_EQUAL( previous, 31 );
""")

x.unit(f"{range}(): traverse in descending key order", f"""
  int previous;
  for(i = 0; i < 32; ++i) {type.set(t, "(i*7)%32", "i")};
  TEST_EQUAL( {type.size(t)}, 32 );
  previous = 32;
  for({r} = {range.new(t)}; !{range.empty(r)}; {range.move_back(r)}) {{
    TEST_TRUE( *{range.index_back_view(r)} < previous );
    previous = *{range.index_back_view(r)};
  }}
  TEST_EQUAL( previous, 0 );
""")


t1 = type.variable("t1")
t2 = type.variable("t2")

x.setup(f"""
  {t1.definition};
  {t2.definition};
  {type.create(t1)};
  {type.create(t2)};
""")
x.cleanup(f"""
  {type.destroy(t1)};
  {type.destroy(t2)};
""")

x.unit(f"{type.equal}(): compare equal empty maps", f"""
  TEST_TRUE( {type.equal(t1, t2)} );
""")

x.unit(f"{type.copy}(): copy empty map", f"""
  {type.copy(t2, t1)};
  TEST_TRUE( {type.equal(t1, t2)} );
""")

x.unit(f"{type.copy}(): copy !empty map", f"""
  {type.set(t1, 0, 0)};
  {type.set(t1, 1, 1)};
  {type.set(t1, 2, 2)};
  {type.copy(t2, t1)};
  TEST_TRUE( {type.equal(t1, t2)} );
  TEST_EQUAL( {type.hash(t1)}, {type.hash(t2)} );
  TEST_EQUAL( {type.size(t2)}, 3 );
  TEST_TRUE( {type.indexed(t2, 0)} );
  TEST_TRUE( {type.indexed(t2, 1)} );
  TEST_TRUE( {type.indexed(t2, 2)} );
""")

x.unit(f"{type.equal}(): compare maps of different sizes", f"""
  {type.set(t1, 3, 3)};
  TEST_FALSE( {type.equal(t1, t2)} );
""")

x.unit(f"{type.compare}(): compare equal maps", f"""
  {type.set(t1, 0, 0)};
  {type.set(t1, 1, 1)};
  {type.set(t2, 0, 0)};
  {type.set(t2, 1, 1)};
  TEST_EQUAL( {type.compare(t1, t2)}, 0 );
""")
