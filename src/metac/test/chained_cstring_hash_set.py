from metac.test import *
from metac.chained_hash_set import Set
from metac.test.cstring import cstring, s

x = Type(type := Set("chained_cstring_hash_set", cstring))

t = type.variable("t")


x.setup(f"""
  {t.definition};
  {type.create(t)};
""")
x.cleanup(f"""
  {type.destroy(t)};
""")

x.unit(f"{type.empty}(): test empty set", f"""
  TEST_TRUE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 0 );
""")

x.unit(f"{type.put}(): put new element into empty set", f"""
  TEST_TRUE( {type.put(t, s("hello"))} );
  TEST_FALSE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 1 );
""")

x.unit(f"{type.put}(): put the same element twice", f"""
  TEST_TRUE( {type.put(t, s("hello"))} );
  TEST_FALSE( {type.put(t, s("hello"))} );
  TEST_EQUAL( {type.size(t)}, 1 );
""")

x.unit(f"{type.remove}(): remove !existing element", f"""
  TEST_FALSE( {type.remove(t, s("hello"))} );
""")

x.unit(f"{type.contains}(): !contained in empty set", f"""
  TEST_FALSE( {type.contains(t, s("hello"))} );
""")

x.unit(f"{type.hash}(): hash empty set", f"""
  {type.hash(t)};
""")


x.setup(f"""
  {t.definition};
  {type.create(t)};
  {type.put(t, s("hello"))};
""")
x.cleanup(f"""
  {type.destroy(t)};
""")

x.unit(f"{type.contains}(): contained in !empty set", f"""
  TEST_TRUE( {type.contains(t, s("hello"))} );
""")

x.unit(f"{type.contains}(): !contained in !empty set", f"""
  TEST_FALSE( {type.contains(t, s("Hello"))} );
""")

x.unit(f"{type.remove}(): remove existing element", f"""
  TEST_TRUE( {type.remove(t, s("hello"))} );
  TEST_TRUE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 0 );
""")

x.unit(f"{type.find_view}(): find existing element", f"""
  TEST_EQUAL_CHARS( {type.find_view(t, s("hello"))}, {s("hello")} );
""")

x.unit(f"{type.find_view}(): find !existing element", f"""
  TEST_TRUE( {type.find_view(t, s("bye"))} == NULL );
""")

x.unit(f"{type.hash}(): hash !empty set", f"""
  {type.hash(t)};
""")


range = type.range
r = range.variable("r")

x.setup(f"""
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
  {type.put(t, s("one"))};
  {type.put(t, s("two"))};
  {type.put(t, s("three"))};
  TEST_EQUAL( {type.size(t)}, 3 );
  {{
    int seen = 0;
    for({r} = {range.new(t)}; !{range.empty(r)}; {range.move_front(r)}) {{
      if(!strcmp({range.front_view(r)}, {s("one")})) seen |= 1;
      else if(!strcmp({range.front_view(r)}, {s("two")})) seen |= 2;
      else if(!strcmp({range.front_view(r)}, {s("three")})) seen |= 4;
    }}
    TEST_EQUAL( seen, 7 );
  }}
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

x.unit(f"{type.copy}(): copy !empty set", f"""
  {type.put(t1, s("one"))};
  {type.put(t1, s("two"))};
  {type.put(t1, s("three"))};
  {type.copy(t2, t1)};
  TEST_TRUE( {type.equal(t1, t2)} );
  TEST_EQUAL( {type.hash(t1)}, {type.hash(t2)} );
  TEST_EQUAL( {type.size(t2)}, 3 );
  TEST_TRUE( {type.contains(t2, s("two"))} );
""")

x.unit(f"{type.equal}(): compare !equal sets of same size", f"""
  {type.put(t1, s("one"))};
  {type.put(t2, s("One"))};
  TEST_FALSE( {type.equal(t1, t2)} );
""")
