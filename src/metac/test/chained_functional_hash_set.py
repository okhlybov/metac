from metac.test import *
from metac.chained_hash_set import Set
from metac.test.functional import unary, helpers


x = Type(type := Set("chained_functional_hash_set", unary), dependencies=[helpers])

t = type.variable("t")
f = unary.variable("f")


x.setup(f"""
  {t.definition};
""")
x.cleanup(f"""
  {type.destroy(t)};
""")

x.unit(f"{type.put}(): put functionals into empty set", f"""
  {type.create(t)};
  TEST_TRUE( {type.put(t, "functional_double")} );
  TEST_TRUE( {type.put(t, "functional_negate")} );
  TEST_EQUAL( {type.size(t)}, 2 );
""")

x.unit(f"{type.put}(): put the same functional twice", f"""
  {type.create(t)};
  TEST_TRUE( {type.put(t, "functional_double")} );
  TEST_FALSE( {type.put(t, "functional_double")} );
  TEST_EQUAL( {type.size(t)}, 1 );
""")

x.unit(f"{type.contains}(): contained functionals", f"""
  {type.create(t)};
  {type.put(t, "functional_double")};
  TEST_TRUE( {type.contains(t, "functional_double")} );
  TEST_FALSE( {type.contains(t, "functional_negate")} );
""")

x.unit(f"{type.find_view}(): find and call the contained functional", f"""
  {f.definition};
  {type.create(t)};
  {type.put(t, "functional_double")};
  {f} = *{type.find_view(t, "functional_double")};
  TEST_EQUAL( {f(8)}, 16 );
  TEST_TRUE( {type.find_view(t, "functional_negate")} == NULL );
""")

x.unit(f"{type.remove}(): remove existing functional", f"""
  {type.create(t)};
  {type.put(t, "functional_double")};
  TEST_TRUE( {type.remove(t, "functional_double")} );
  TEST_TRUE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 0 );
""")

x.unit(f"{type.remove}(): remove !existing functional", f"""
  {type.create(t)};
  {type.put(t, "functional_double")};
  TEST_FALSE( {type.remove(t, "functional_negate")} );
  TEST_EQUAL( {type.size(t)}, 1 );
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

x.unit(f"{range}(): traverse set of functionals", f"""
  int seen = 0;
  {type.put(t, "functional_double")};
  {type.put(t, "functional_negate")};
  for({r} = {range.new(t)}; !{range.empty(r)}; {range.move_front(r)}) {{
    if({range.front(r)} == functional_double) seen |= 1;
    else if({range.front(r)} == functional_negate) seen |= 2;
  }}
  TEST_EQUAL( seen, 3 );
""")

x.unit(f"{range}(): call every functional while traversing", f"""
  {f.definition};
  int seen = 0;
  {type.put(t, "functional_double")};
  {type.put(t, "functional_negate")};
  for({r} = {range.new(t)}; !{range.empty(r)}; {range.move_front(r)}) {{
    {f} = *{range.front_view(r)};
    int result = {f(5)};
    if(result == 10) seen |= 1;
    else if(result == -5) seen |= 2;
  }}
  TEST_EQUAL( seen, 3 );
""")