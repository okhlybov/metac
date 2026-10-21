from metac.test import *
from metac.variant import Variant
from metac.test.custom_composite_arc import type as arc


# A merged variant testing both a primitive and a (heap-owning, shared-reference) composite alternative
x = Type(type := Variant("content_variant", {"amount": "int", "composite": arc}))

t = type.variable("t")
t1 = type.variable("t1")
t2 = type.variable("t2")
p = arc.variable("p")


x.setup(f"""
  {t.definition};
  {type.create(t)};
""")
x.cleanup(f"""
  {type.destroy(t)};
""")

x.unit(f"{type.create}(): create variant in the empty state", f"""
  TEST_TRUE( {type.is_empty(t)} );
  TEST_FALSE( {type.is_amount(t)} );
  TEST_FALSE( {type.is_composite(t)} );
""")

x.unit(f"{type.hash}(): hash of the empty variant", f"""
  {type.hash(t)};
""")

x.unit(f"{type.set_amount}(): set the primitive alternative", f"""
  {type.set_amount(t, 42)};
  TEST_FALSE( {type.is_empty(t)} );
  TEST_TRUE( {type.is_amount(t)} );
  TEST_FALSE( {type.is_composite(t)} );
  TEST_EQUAL( {type.get_amount(t)}, 42 );
""")

x.unit(f"{type.set_composite}(): set the composite alternative", f"""
  {p.definition};
  {arc.create(p, 7)};
  {type.set_composite(t, p)};
  TEST_FALSE( {type.is_empty(t)} );
  TEST_FALSE( {type.is_amount(t)} );
  TEST_TRUE( {type.is_composite(t)} );
  TEST_EQUAL( *{type.get_composite_view(t)}->value, 7 );
  {arc.destroy(p)};
""")

x.unit(f"{type.set_amount}(): switch from the composite alternative destroying it", f"""
  {p.definition};
  {arc.create(p, 7)};
  {type.set_composite(t, p)};
  {arc.destroy(p)};
  {type.set_amount(t, 3)};
  TEST_TRUE( {type.is_amount(t)} );
  TEST_FALSE( {type.is_composite(t)} );
  TEST_EQUAL( {type.get_amount(t)}, 3 );
""")

x.unit(f"{type.set_composite}(): switch between the same composite alternative", f"""
  {p.definition};
  {arc.create(p, 7)};
  {type.set_composite(t, p)};
  {type.set_composite(t, p)};
  TEST_TRUE( {type.is_composite(t)} );
  TEST_EQUAL( *{type.get_composite_view(t)}->value, 7 );
  {arc.destroy(p)};
""")


x.setup(f"""
  {t1.definition};
  {type.create(t1)};
  {t2.definition};
  {type.create(t2)};
""")
x.cleanup(f"""
  {type.destroy(t1)};
  {type.destroy(t2)};
""")

x.unit(f"{type.equal}(): compare empty and primitive variants", f"""
  TEST_TRUE( {type.equal(t1, t2)} );
  {type.set_amount(t2, 5)};
  TEST_FALSE( {type.equal(t1, t2)} );
  {type.set_amount(t1, 5)};
  TEST_TRUE( {type.equal(t1, t2)} );
  {type.set_amount(t2, 6)};
  TEST_FALSE( {type.equal(t1, t2)} );
""")

x.unit(f"{type.equal}(): compare variants sharing the same composite value", f"""
  {p.definition};
  {arc.create(p, 9)};
  {type.set_composite(t1, p)};
  {type.set_composite(t2, p)};
  {arc.destroy(p)};
  TEST_TRUE( {type.equal(t1, t2)} );
  TEST_TRUE( {type.is_composite(t1)} );
  TEST_TRUE( {type.is_composite(t2)} );
""")

x.unit(f"{type.hash}(): hash equal variants", f"""
  {p.definition};
  {arc.create(p, 9)};
  {type.set_composite(t1, p)};
  {type.set_composite(t2, p)};
  {arc.destroy(p)};
  TEST_EQUAL( {type.hash(t1)}, {type.hash(t2)} );
""")

x.unit(f"{type.copy}(): copy variant holding the composite alternative", f"""
  {p.definition};
  {arc.create(p, 13)};
  {type.set_composite(t1, p)};
  {arc.destroy(p)};
  {type.copy(t2, t1)};
  TEST_TRUE( {type.equal(t1, t2)} );
  TEST_TRUE( {type.is_composite(t2)} );
  TEST_EQUAL( *{type.get_composite_view(t2)}->value, 13 );
""")

x.unit(f"{type.move}(): move variant holding the composite alternative", f"""
  {p.definition};
  {arc.create(p, 17)};
  {type.set_composite(t1, p)};
  {arc.destroy(p)};
  {type.move(t2, t1)};
  TEST_TRUE( {type.is_composite(t2)} );
  TEST_EQUAL( *{type.get_composite_view(t2)}->value, 17 );
  TEST_TRUE( {type.is_empty(t1)} );
""")