from metac.test import *
from metac.rb_set import Set

x = Type(type := Set("int_rb_set", "int"))

t = type.variable("t")


x.setup(f"""
  {t.definition};
""")
x.cleanup(f"""
  {type.destroy(t)};
""")

x.unit(f"{type.create}(): create empty set", f"""
  {type.create(t)};
  TEST_TRUE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 0 );
""")

x.unit(f"{type.put}(): put new element into empty set", f"""
  {type.create(t)};
  TEST_TRUE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 0 );
  TEST_TRUE( {type.put(t, 0)} );
  TEST_FALSE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 1 );
""")

x.unit(f"{type.put}(): put the same element twice", f"""
  {type.create(t)};
  TEST_TRUE( {type.put(t, 0)} );
  TEST_FALSE( {type.put(t, 0)} );
  TEST_EQUAL( {type.size(t)}, 1 );
""")

x.unit(f"{type.remove}(): remove !existing element", f"""
  {type.create(t)};
  TEST_TRUE( {type.empty(t)} );
  TEST_FALSE( {type.remove(t, 0)} );
""")

x.unit(f"{type.contains}(): !contained in empty set", f"""
  {type.create(t)};
  TEST_FALSE( {type.contains(t, 0)} );
""")

x.unit(f"{type.hash}(): hash empty set", f"""
  {type.create(t)};
  {type.hash(t)};
""")

x.unit(f"{type.compare}(): compare empty sets", f"""
  {type.create(t)};
  {{ {type.variable("t2").definition};
     {type.create("&t2")};
     TEST_EQUAL( {type.compare(t, "&t2")}, 0 );
     {type.destroy("&t2")};
  }}
""")


x.setup(f"""
  {t.definition};
  {type.create(t)};
  {type.put(t, 0)};
""")
x.cleanup(f"""
  {type.destroy(t)};
""")

x.unit(f"{type.contains}(): contained in !empty set", f"""
  TEST_TRUE( {type.contains(t, 0)} );
""")

x.unit(f"{type.contains}(): !contained in !empty set", f"""
  TEST_FALSE( {type.contains(t, -1)} );
""")

x.unit(f"{type.remove}(): remove existing element", f"""
  TEST_TRUE( {type.remove(t, 0)} );
  TEST_TRUE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 0 );
""")

x.unit(f"{type.find_view}(): find existing element", f"""
  TEST_EQUAL( *{type.find_view(t, 0)}, 0 );
""")

x.unit(f"{type.find_view}(): find !existing element", f"""
  TEST_TRUE( {type.find_view(t, -1)} == NULL );
""")

x.unit(f"{type.hash}(): hash !empty set", f"""
  {type.hash(t)};
""")

x.unit(f"{type.put}/{type.remove}: churn does not grow the set", f"""
  int i;
  for(i = 1; i < 64; ++i) {{
    TEST_TRUE( {type.put(t, "i")} );
    TEST_EQUAL( {type.size(t)}, 2 );
    TEST_TRUE( {type.remove(t, "i")} );
    TEST_EQUAL( {type.size(t)}, 1 );
  }}
""")

x.unit(f"{type.put}/{type.remove}: removal keeps the set consistent", f"""
  int i;
  for(i = 1; i < 32; ++i) {{ TEST_TRUE( {type.put(t, "i")} ); }}
  TEST_EQUAL( {type.size(t)}, 32 );
  for(i = 0; i < 32; ++i) {{
    TEST_TRUE( {type.remove(t, "i")} );
    TEST_EQUAL( {type.size(t)}, 31-i );
    TEST_FALSE( {type.contains(t, "i")} );
  }}
  TEST_TRUE( {type.empty(t)} );
""")


range = type.range
r = range.variable("r")

x.setup(f"""
  int i;
  {r.definition};
  {t.definition};
  {type.create(t)};
""")
x.cleanup(f"""
  {type.destroy(t)};
""")

x.unit(f"{range}(): traverse empty set", f"""
  {r} = {range.new(t)};
  TEST_TRUE( {range.empty(r)} );
""")

x.unit(f"{range}(): traverse !empty set", f"""
  unsigned mask = 0;
  for(i = 0; i < 32; ++i) {type.put(t, "i")};
  TEST_EQUAL( {type.size(t)}, 32 );
  for({r} = {range.new(t)}; !{range.empty(r)}; {range.move_front(r)}) {{
    mask |= 1 << {range.front(r)};
  }}
  TEST_EQUAL( mask, 0xFFFFFFFF );
""")

x.unit(f"{range}(): traverse in ascending order", f"""
  int previous;
  for(i = 0; i < 32; ++i) {type.put(t, "(i*7)%32")};
  TEST_EQUAL( {type.size(t)}, 32 );
  previous = -1;
  for({r} = {range.new(t)}; !{range.empty(r)}; {range.move_front(r)}) {{
    TEST_TRUE( *{range.front_view(r)} > previous );
    previous = *{range.front_view(r)};
  }}
  TEST_EQUAL( previous, 31 );
""")

x.unit(f"{range}(): backward traversal in descending order", f"""
  int previous;
  for(i = 0; i < 32; ++i) {type.put(t, "(i*7)%32")};
  TEST_EQUAL( {type.size(t)}, 32 );
  previous = 32;
  for({r} = {range.new(t)}; !{range.empty(r)}; {range.move_back(r)}) {{
    TEST_TRUE( *{range.back_view(r)} < previous );
    previous = *{range.back_view(r)};
  }}
  TEST_EQUAL( previous, 0 );
""")

x.unit(f"{range}(): traversal survives the churn", f"""
  int previous;
  for(i = 0; i < 256; ++i) {{ TEST_TRUE( {type.put(t, "(i*137)%256")} ); }}
  TEST_EQUAL( {type.size(t)}, 256 );
  for(i = 0; i < 256; i += 2) {{ TEST_TRUE( {type.remove(t, "i")} ); }}
  TEST_EQUAL( {type.size(t)}, 128 );
  previous = -2;
  for({r} = {range.new(t)}; !{range.empty(r)}; {range.move_front(r)}) {{
    TEST_TRUE( *{range.front_view(r)} % 2 == 1 );
    TEST_TRUE( *{range.front_view(r)} > previous );
    previous = *{range.front_view(r)};
  }}
  TEST_EQUAL( previous, 255 );
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

x.unit(f"{type.equal}(): compare equal empty sets", f"""
  TEST_TRUE( {type.equal(t1, t2)} );
""")

x.unit(f"{type.copy}(): copy empty set", f"""
  {type.copy(t2, t1)};
  TEST_TRUE( {type.equal(t1, t2)} );
""")

x.unit(f"{type.copy}(): copy !empty set", f"""
  {type.put(t1, 0)};
  {type.put(t1, 1)};
  {type.put(t1, 2)};
  {type.copy(t2, t1)};
  TEST_TRUE( {type.equal(t1, t2)} );
  TEST_EQUAL( {type.hash(t1)}, {type.hash(t2)} );
  TEST_EQUAL( {type.size(t2)}, 3 );
  TEST_TRUE( {type.contains(t2, 0)} );
  TEST_TRUE( {type.contains(t2, 1)} );
  TEST_TRUE( {type.contains(t2, 2)} );
""")

x.unit(f"{type.copy}/{type.equal}: large copy preserves the content", f"""
  int i;
  for(i = 0; i < 128; ++i) {type.put(t1, "(i*29)%128")};
  {type.copy(t2, t1)};
  TEST_TRUE( {type.equal(t1, t2)} );
  TEST_EQUAL( {type.hash(t1)}, {type.hash(t2)} );
""")

x.unit(f"{type.equal}(): compare sets of different sizes", f"""
  {type.put(t1, 3)};
  TEST_FALSE( {type.equal(t1, t2)} );
""")

x.unit(f"{type.equal}(): compare !equal sets of same size", f"""
  {type.put(t1, 0)};
  {type.put(t2, 1)};
  TEST_FALSE( {type.equal(t1, t2)} );
""")

x.unit(f"{type.compare}(): compare equal sets", f"""
  {type.put(t1, 0)};
  {type.put(t1, 1)};
  {type.put(t2, 0)};
  {type.put(t2, 1)};
  TEST_EQUAL( {type.compare(t1, t2)}, 0 );
""")

x.unit(f"{type.compare}(): compare !equal sets", f"""
  {type.put(t1, 0)};
  {type.put(t1, 1)};
  {type.put(t1, 2)};
  {type.put(t2, 0)};
  {type.put(t2, 1)};
  {type.put(t2, 3)};
  TEST_TRUE( {type.compare(t1, t2)} < 0 );
  TEST_TRUE( {type.compare(t2, t1)} > 0 );
""")

x.unit(f"{type.compare}(): compare prefix set", f"""
  {type.put(t1, 0)};
  {type.put(t2, 0)};
  {type.put(t2, 1)};
  TEST_TRUE( {type.compare(t1, t2)} < 0 );
  TEST_TRUE( {type.compare(t2, t1)} > 0 );
""")


o = type.variable("o")

x.setup(f"""
  {r.definition};
  {t.definition};
  {o.definition};
  {type.create(t)};
  {type.create(o)};
""")
x.cleanup(f"""
  {type.destroy(t)};
  {type.destroy(o)};
""")

x.unit(f"{type.apply_union}(): union adds elements from other set", f"""
  {type.put(t, 1)}; {type.put(t, 2)}; {type.put(t, 3)};
  {type.put(o, 3)}; {type.put(o, 4)}; {type.put(o, 5)};
  TEST_EQUAL( {type.apply_union(t, o)}, 2 );
  TEST_EQUAL( {type.size(t)}, 5 );
  TEST_TRUE( {type.contains(t, 4)} );
  TEST_TRUE( {type.contains(t, 5)} );
  TEST_EQUAL( {type.size(o)}, 3 );
""")

x.unit(f"{type.apply_difference}(): difference removes common elements", f"""
  {type.put(t, 1)}; {type.put(t, 2)}; {type.put(t, 3)};
  {type.put(o, 2)}; {type.put(o, 3)}; {type.put(o, 4)};
  TEST_EQUAL( {type.apply_difference(t, o)}, 2 );
  TEST_EQUAL( {type.size(t)}, 1 );
  TEST_TRUE( {type.contains(t, 1)} );
""")

x.unit(f"{type.apply_intersection}(): intersection keeps only common elements", f"""
  {type.put(t, 1)}; {type.put(t, 2)}; {type.put(t, 3)};
  {type.put(o, 2)}; {type.put(o, 3)}; {type.put(o, 4)};
  TEST_EQUAL( {type.apply_intersection(t, o)}, 1 );
  TEST_EQUAL( {type.size(t)}, 2 );
  TEST_TRUE( {type.contains(t, 2)} );
  TEST_TRUE( {type.contains(t, 3)} );
""")

x.unit(f"{type.apply_symmetric_difference}(): keeps uncommon elements", f"""
  {type.put(t, 1)}; {type.put(t, 2)}; {type.put(t, 3)};
  {type.put(o, 2)}; {type.put(o, 3)}; {type.put(o, 4)};
  TEST_EQUAL( {type.apply_symmetric_difference(t, o)}, 3 );
  TEST_EQUAL( {type.size(t)}, 2 );
  TEST_TRUE( {type.contains(t, 1)} );
  TEST_TRUE( {type.contains(t, 4)} );
""")

x.unit(f"{type.is_subset}(): subset relations", f"""
  {type.put(t, 1)}; {type.put(t, 2)};
  {type.put(o, 1)}; {type.put(o, 2)}; {type.put(o, 3)};
  TEST_TRUE( {type.is_subset(t, o)} );
  TEST_TRUE( {type.is_superset(o, t)} );
  TEST_FALSE( {type.is_subset(o, t)} );
""")
