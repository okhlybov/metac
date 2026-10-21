from metac.test import *
from metac.vector import Vector
from metac.test.functional import unary, helpers


x = Type(type := Vector("functional_vector", unary), dependencies=[helpers])

t = type.variable("t")
t2 = type.variable("t2")

f = unary.variable("f")


x.setup(f"""
  {t.definition};
  {type.create(t)};
""")
x.cleanup(f"""
  {type.destroy(t)};
""")

x.unit(f"{type.empty}(): test empty vector", f"""
  TEST_TRUE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 0 );
""")

x.unit(f"{type.create_size}(): default initializes elements with null pointers", f"""
  {type.create_size(t, 2)};
  TEST_EQUAL( {type.size(t)}, 2 );
  TEST_TRUE( *{type.view(t, 0)} == NULL );
  TEST_TRUE( *{type.view(t, 1)} == NULL );
""")

x.unit(f"{type.set}(): set element then call through the view", f"""
  {f.definition};
  {type.create_size(t, 2)};
  {type.set(t, 0, "functional_double")};
  {f} = *{type.view(t, 0)};
  TEST_EQUAL( {f(21)}, 42 );
""")

x.unit(f"{type.get}(): get element then call the returned value", f"""
  {f.definition};
  {type.create_size(t, 2)};
  {type.set(t, 0, "functional_double")};
  {f} = {type.get(t, 0)};
  TEST_EQUAL( {f(4)}, 8 );
""")

x.unit(f"{type.contains}(): contained element", f"""
  {type.create_size(t, 2)};
  {type.set(t, 0, "functional_double")};
  TEST_TRUE( {type.contains(t, "functional_double")} );
  TEST_FALSE( {type.contains(t, "functional_negate")} );
""")


x.setup(f"""
  {t.definition};
  {t2.definition};
  {type.create(t)};
  {type.create(t2)};
""")
x.cleanup(f"""
  {type.destroy(t)};
  {type.destroy(t2)};
""")

x.unit(f"{type.copy}(): copy vector of functionals", f"""
  {f.definition};
  {type.create_size(t, 2)};
  {type.set(t, 0, "functional_double")};
  {type.set(t, 1, "functional_negate")};
  {type.copy(t2, t)};
  TEST_TRUE( {type.equal(t, t2)} );
  TEST_EQUAL( {type.hash(t)}, {type.hash(t2)} );
  {f} = *{type.view(t2, 0)};
  TEST_EQUAL( {f(3)}, 6 );
  {f} = *{type.view(t2, 1)};
  TEST_EQUAL( {f(3)}, -3 );
""")

x.unit(f"{type.set}(): overwrite element", f"""
  {type.create_size(t, 2)};
  {type.set(t, 0, "functional_double")};
  {type.set(t, 0, "functional_negate")};
  TEST_TRUE( {type.contains(t, "functional_negate")} );
  TEST_FALSE( {type.contains(t, "functional_double")} );
""")