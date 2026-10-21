from metac.test import *
from metac.flat_multiset import Set as Multiset
from metac.test.cstring import cstring, s

x = Type(type := Multiset("cstring_flat_multiset", cstring))

t = type.variable("t")

x.setup(f"""
  {t.definition};
""")
x.cleanup(f"""
  {type.destroy(t)};
""")

x.unit("destructible duplicates: put, wipe, and remove string elements", f"""
  {type.create(t)};
  {type.put(t, s("beta"))};
  {type.put(t, s("alpha"))};
  {type.put(t, s("beta"))};
  {type.put(t, s("gamma"))};
  {type.put(t, s("beta"))};

  TEST_EQUAL( {type.size(t)}, 5 );
  TEST_EQUAL( {type.count(t, s("beta"))}, 3 );
  TEST_EQUAL( {type.count(t, s("alpha"))}, 1 );
  TEST_EQUAL( {type.count(t, s("gamma"))}, 1 );

  /* Remove one beta */
  TEST_TRUE( {type.remove(t, s("beta"))} );
  TEST_EQUAL( {type.size(t)}, 4 );
  TEST_EQUAL( {type.count(t, s("beta"))}, 2 );

  /* Wipe remaining betas */
  TEST_EQUAL( {type.wipe(t, s("beta"))}, 2 );
  TEST_EQUAL( {type.size(t)}, 2 );
  TEST_EQUAL( {type.count(t, s("beta"))}, 0 );

  /* Wipe alpha */
  TEST_EQUAL( {type.wipe(t, s("alpha"))}, 1 );
  TEST_EQUAL( {type.size(t)}, 1 );

  /* Wipe gamma */
  TEST_EQUAL( {type.wipe(t, s("gamma"))}, 1 );
  TEST_TRUE( {type.empty(t)} );
""")
