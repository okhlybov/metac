from metac.test import *
from metac.intrusive_hash_set import Set
from metac.test.primitive_arc import type

states = {
  "empty": (
    lambda element: f"{element} == ({type})(size_t)2 /* empty? */",
    lambda element: f"{element} = ({type})(size_t)2 /* empty! */",
  ),
  "deleted": (
    lambda element: f"{element} == ({type})(size_t)1 /* deleted? */",
    lambda element: f"{element} = ({type})(size_t)1 /* deleted! */",
  ),
}

x = Type(type := Set("intrusive_primitive_arc_hash_set", type, states))

t = type.variable("t")
t1 = type.variable("t1")
t2 = type.variable("t2")

xtype = type.element
z = xtype.variable("z")

range = type.range
r = range.variable("r")


x.setup(f"""
  {t.definition};
  {z.definition};
  {xtype.create(z)};
""")
x.cleanup(f"""
  {type.destroy(t)};
  {xtype.destroy(z)};
""")

x.unit(f"{type.create_size}(): create empty set with preferred capacity", f"""
  {type.create_size(t, 1024+11)};
  TEST_TRUE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 0 );
  TEST_TRUE( {type.put(t, z)} );
  TEST_FALSE( {type.empty(t)} );
""")

x.unit(f"{type.create_size}(): create empty set with zero size", f"""
  {type.create_size(t, 0)};
  TEST_TRUE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 0 );
  TEST_TRUE( {type.put(t, z)} );
  TEST_FALSE( {type.empty(t)} );
""")

x.unit(f"{type.create_size}(): shrink empty set", f"""
  {type.create_size(t, 1024+11)};
  TEST_TRUE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 0 );
  {type.resize(t, 0)};
""")

x.setup(f"""
  {t.definition};
  {z.definition};
  {xtype.create(z)};
  {type.create(t)};
""")
x.cleanup(f"""
  {type.destroy(t)};
  {xtype.destroy(z)};
""")

x.unit(f"{type.hash}(): hash of !empty set", f"""
  TEST_TRUE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 0 );
  TEST_TRUE( {type.put(t, z)} );
  {type.hash(t)};
""")

x.unit(f"{type.put}(): repeated put", f"""
  TEST_TRUE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 0 );
  TEST_TRUE( {type.put(t, z)} );
  TEST_FALSE( {type.put(t, z)} );
  TEST_EQUAL( {type.size(t)}, 1);
""")