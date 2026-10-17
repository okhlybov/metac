from autoc.test import *
from autoc.bit_array import Array

x = Type(type := Array("test_bitarray", 20))

t = type.variable("t")
t1 = type.variable("t1")
t2 = type.variable("t2")
t3 = type.variable("t3")


x.setup(f"""
  {t.definition};
  {type.create(t)};
""")
x.cleanup("")


x.unit(f"{type.capacity}(): capacity is 20", f"""
  TEST_EQUAL( {type.capacity(t)}, 20 );
""")

x.unit(f"{type.none}(): new bitset is empty", f"""
  TEST_TRUE( {type.none(t)} );
  TEST_FALSE( {type.any(t)} );
  TEST_EQUAL( {type.count(t)}, 0 );
""")

x.unit(f"{type.set}()/test(): set and test bits", f"""
  {type.set(t, 0)};
  {type.set(t, 7)};
  {type.set(t, 19)};
  TEST_TRUE( {type.test(t, 0)} );
  TEST_TRUE( {type.test(t, 7)} );
  TEST_TRUE( {type.test(t, 19)} );
  TEST_FALSE( {type.test(t, 1)} );
  TEST_FALSE( {type.test(t, 18)} );
  TEST_TRUE( {type.any(t)} );
  TEST_FALSE( {type.none(t)} );
  TEST_EQUAL( {type.count(t)}, 3 );
""")

x.unit(f"{type.clear}(): clear a set bit", f"""
  {type.set(t, 5)};
  {type.set(t, 10)};
  TEST_TRUE( {type.test(t, 5)} );
  {type.clear(t, 5)};
  TEST_FALSE( {type.test(t, 5)} );
  TEST_TRUE( {type.test(t, 10)} );
  TEST_EQUAL( {type.count(t)}, 1 );
""")

x.unit(f"{type.flip}(): flip a bit", f"""
  TEST_FALSE( {type.test(t, 3)} );
  {type.flip(t, 3)};
  TEST_TRUE( {type.test(t, 3)} );
  {type.flip(t, 3)};
  TEST_FALSE( {type.test(t, 3)} );
""")

x.unit(f"{type.set_all}(): set all bits", f"""
  {type.set_all(t)};
  TEST_EQUAL( {type.count(t)}, 20 );
  TEST_TRUE( {type.test(t, 0)} );
  TEST_TRUE( {type.test(t, 7)} );
  TEST_TRUE( {type.test(t, 15)} );
  TEST_TRUE( {type.test(t, 19)} );
  TEST_TRUE( {type.any(t)} );
""")

x.unit(f"{type.flip_all}(): flip all bits", f"""
  {type.flip_all(t)};
  TEST_EQUAL( {type.count(t)}, 20 );
  TEST_TRUE( {type.test(t, 0)} );
  TEST_TRUE( {type.test(t, 19)} );
  {type.flip_all(t)};
  TEST_EQUAL( {type.count(t)}, 0 );
  TEST_TRUE( {type.none(t)} );
""")

x.unit(f"{type.flip_all}(): flip on partial state", f"""
  {type.set(t, 0)};
  {type.set(t, 5)};
  {type.set(t, 19)};
  {type.flip_all(t)};
  TEST_FALSE( {type.test(t, 0)} );
  TEST_FALSE( {type.test(t, 5)} );
  TEST_FALSE( {type.test(t, 19)} );
  TEST_TRUE( {type.test(t, 1)} );
  TEST_TRUE( {type.test(t, 18)} );
  TEST_EQUAL( {type.count(t)}, 17 );
""")

x.unit(f"{type.find_first}(): find first set bit", f"""
  TEST_EQUAL( {type.find_first(t)}, 20 );
  {type.set(t, 12)};
  {type.set(t, 5)};
  {type.set(t, 18)};
  TEST_EQUAL( {type.find_first(t)}, 5 );
  {type.clear(t, 5)};
  TEST_EQUAL( {type.find_first(t)}, 12 );
""")

x.unit(f"{type.equal}(): equality", f"""
  {t1.definition};
  {t2.definition};
  {type.create(t1)};
  {type.create(t2)};
  TEST_TRUE( {type.equal(t1, t2)} );
  {type.set(t1, 3)};
  TEST_FALSE( {type.equal(t1, t2)} );
  {type.set(t2, 3)};
  TEST_TRUE( {type.equal(t1, t2)} );
""")

x.unit(f"{type.hash}(): consistent hashing", f"""
  {t1.definition};
  {t2.definition};
  {type.create(t1)};
  {type.create(t2)};
  TEST_EQUAL( {type.hash(t1)}, {type.hash(t2)} );
  {type.set(t1, 7)};
  {type.set(t2, 7)};
  TEST_EQUAL( {type.hash(t1)}, {type.hash(t2)} );
""")

x.unit(f"{type.copy}(): copy bitset", f"""
  {t1.definition};
  {t2.definition};
  {type.create(t1)};
  {type.set(t1, 0)};
  {type.set(t1, 10)};
  {type.set(t1, 19)};
  {type.copy(t2, t1)};
  TEST_TRUE( {type.equal(t1, t2)} );
  TEST_EQUAL( {type.count(t2)}, 3 );
  TEST_TRUE( {type.test(t2, 0)} );
  TEST_TRUE( {type.test(t2, 10)} );
  TEST_TRUE( {type.test(t2, 19)} );
""")

x.unit(f"{type.apply_union}(): union", f"""
  {t1.definition};
  {t2.definition};
  {type.create(t1)};
  {type.create(t2)};
  {type.set(t1, 0)};
  {type.set(t1, 5)};
  {type.set(t2, 5)};
  {type.set(t2, 10)};
  {type.apply_union(t1, t2)};
  TEST_TRUE( {type.test(t1, 0)} );
  TEST_TRUE( {type.test(t1, 5)} );
  TEST_TRUE( {type.test(t1, 10)} );
  TEST_EQUAL( {type.count(t1)}, 3 );
""")

x.unit(f"{type.apply_intersection}(): intersection", f"""
  {t1.definition};
  {t2.definition};
  {type.create(t1)};
  {type.create(t2)};
  {type.set(t1, 0)};
  {type.set(t1, 5)};
  {type.set(t1, 10)};
  {type.set(t2, 5)};
  {type.set(t2, 10)};
  {type.set(t2, 15)};
  {type.apply_intersection(t1, t2)};
  TEST_FALSE( {type.test(t1, 0)} );
  TEST_TRUE( {type.test(t1, 5)} );
  TEST_TRUE( {type.test(t1, 10)} );
  TEST_FALSE( {type.test(t1, 15)} );
  TEST_EQUAL( {type.count(t1)}, 2 );
""")

x.unit(f"{type.apply_difference}(): difference", f"""
  {t1.definition};
  {t2.definition};
  {type.create(t1)};
  {type.create(t2)};
  {type.set(t1, 0)};
  {type.set(t1, 5)};
  {type.set(t1, 10)};
  {type.set(t2, 5)};
  {type.set(t2, 15)};
  {type.apply_difference(t1, t2)};
  TEST_TRUE( {type.test(t1, 0)} );
  TEST_FALSE( {type.test(t1, 5)} );
  TEST_TRUE( {type.test(t1, 10)} );
  TEST_EQUAL( {type.count(t1)}, 2 );
""")

x.unit(f"{type.apply_symmetric_difference}(): symmetric difference", f"""
  {t1.definition};
  {t2.definition};
  {type.create(t1)};
  {type.create(t2)};
  {type.set(t1, 0)};
  {type.set(t1, 5)};
  {type.set(t2, 5)};
  {type.set(t2, 10)};
  {type.apply_symmetric_difference(t1, t2)};
  TEST_TRUE( {type.test(t1, 0)} );
  TEST_FALSE( {type.test(t1, 5)} );
  TEST_TRUE( {type.test(t1, 10)} );
  TEST_EQUAL( {type.count(t1)}, 2 );
""")

x.unit(f"{type.create_union}(): constructing union from immutable sources", f"""
  {t1.definition};
  {t2.definition};
  {t3.definition};
  {type.create(t1)};
  {type.create(t2)};
  {type.set(t1, 0)};
  {type.set(t1, 5)};
  {type.set(t2, 5)};
  {type.set(t2, 10)};
  {type.create_union(t3, t1, t2)};
  TEST_TRUE( {type.test(t3, 0)} );
  TEST_TRUE( {type.test(t3, 5)} );
  TEST_TRUE( {type.test(t3, 10)} );
  TEST_EQUAL( {type.count(t3)}, 3 );
  /* Inputs unmodified */
  TEST_EQUAL( {type.count(t1)}, 2 );
  TEST_EQUAL( {type.count(t2)}, 2 );
""")

x.unit(f"{type.create_intersection}(): constructing intersection from immutable sources", f"""
  {t1.definition};
  {t2.definition};
  {t3.definition};
  {type.create(t1)};
  {type.create(t2)};
  {type.set(t1, 0)};
  {type.set(t1, 5)};
  {type.set(t1, 10)};
  {type.set(t2, 5)};
  {type.set(t2, 10)};
  {type.set(t2, 15)};
  {type.create_intersection(t3, t1, t2)};
  TEST_FALSE( {type.test(t3, 0)} );
  TEST_TRUE( {type.test(t3, 5)} );
  TEST_TRUE( {type.test(t3, 10)} );
  TEST_FALSE( {type.test(t3, 15)} );
  TEST_EQUAL( {type.count(t3)}, 2 );
  /* Inputs unmodified */
  TEST_EQUAL( {type.count(t1)}, 3 );
  TEST_EQUAL( {type.count(t2)}, 3 );
""")

x.unit(f"{type.create_difference}(): constructing difference from immutable sources", f"""
  {t1.definition};
  {t2.definition};
  {t3.definition};
  {type.create(t1)};
  {type.create(t2)};
  {type.set(t1, 0)};
  {type.set(t1, 5)};
  {type.set(t1, 10)};
  {type.set(t2, 5)};
  {type.set(t2, 15)};
  {type.create_difference(t3, t1, t2)};
  TEST_TRUE( {type.test(t3, 0)} );
  TEST_FALSE( {type.test(t3, 5)} );
  TEST_TRUE( {type.test(t3, 10)} );
  TEST_EQUAL( {type.count(t3)}, 2 );
  /* Inputs unmodified */
  TEST_EQUAL( {type.count(t1)}, 3 );
  TEST_EQUAL( {type.count(t2)}, 2 );
""")

x.unit(f"{type.create_symmetric_difference}(): constructing symmetric difference from immutable sources", f"""
  {t1.definition};
  {t2.definition};
  {t3.definition};
  {type.create(t1)};
  {type.create(t2)};
  {type.set(t1, 0)};
  {type.set(t1, 5)};
  {type.set(t2, 5)};
  {type.set(t2, 10)};
  {type.create_symmetric_difference(t3, t1, t2)};
  TEST_TRUE( {type.test(t3, 0)} );
  TEST_FALSE( {type.test(t3, 5)} );
  TEST_TRUE( {type.test(t3, 10)} );
  TEST_EQUAL( {type.count(t3)}, 2 );
  /* Inputs unmodified */
  TEST_EQUAL( {type.count(t1)}, 2 );
  TEST_EQUAL( {type.count(t2)}, 2 );
""")

x.unit(f"{type.is_subset}(): subset test", f"""
  {t1.definition};
  {t2.definition};
  {type.create(t1)};
  {type.create(t2)};
  TEST_TRUE( {type.is_subset(t1, t2)} );
  {type.set(t1, 5)};
  TEST_FALSE( {type.is_subset(t1, t2)} );
  {type.set(t2, 5)};
  {type.set(t2, 10)};
  TEST_TRUE( {type.is_subset(t1, t2)} );
  {type.set(t1, 10)};
  TEST_TRUE( {type.is_subset(t1, t2)} );
  {type.set(t1, 15)};
  TEST_FALSE( {type.is_subset(t1, t2)} );
""")
