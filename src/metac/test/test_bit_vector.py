from metac.test import *
from metac.bit_vector import Vector

x = Type(type := Vector("test_bitvector"))

t = type.variable("t")
t1 = type.variable("t1")
t2 = type.variable("t2")
t3 = type.variable("t3")


x.setup(f"""
  {t.definition};
  {type.create(t)};
""")
x.cleanup(f"""
  {type.destroy(t)};
""")


x.unit(f"{type.empty}(): new bitvector is empty", f"""
  TEST_TRUE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 0 );
  TEST_TRUE( {type.none(t)} );
  TEST_FALSE( {type.any(t)} );
  TEST_EQUAL( {type.count(t)}, 0 );
""")

x.unit(f"{type.push}(): push bits to bitvector", f"""
  {type.push(t, 1)};
  {type.push(t, 0)};
  {type.push(t, 1)};
  TEST_FALSE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 3 );
  TEST_EQUAL( {type.get(t, 0)}, 1 );
  TEST_EQUAL( {type.get(t, 1)}, 0 );
  TEST_EQUAL( {type.get(t, 2)}, 1 );
  TEST_EQUAL( {type.count(t)}, 2 );
  TEST_TRUE( {type.any(t)} );
  TEST_FALSE( {type.all(t)} );
""")

x.unit(f"{type.pop}(): pop bits from bitvector", f"""
  {type.push(t, 1)};
  {type.push(t, 0)};
  TEST_EQUAL( {type.size(t)}, 2 );
  TEST_EQUAL( {type.pop(t)}, 0 );
  TEST_EQUAL( {type.size(t)}, 1 );
  TEST_EQUAL( {type.pop(t)}, 1 );
  TEST_EQUAL( {type.size(t)}, 0 );
  TEST_TRUE( {type.empty(t)} );
""")

x.unit(f"{type.reserve}()/{type.compact}(): capacity management", f"""
  {type.reserve(t, 200)};
  TEST_TRUE( {type.capacity(t)} >= 200 );
  {type.push(t, 1)};
  {type.push(t, 0)};
  {type.push(t, 1)};
  TEST_EQUAL( {type.size(t)}, 3 );
  {type.compact(t)};
  TEST_TRUE( {type.capacity(t)} >= 3 );
  TEST_TRUE( {type.capacity(t)} < 200 );
  TEST_EQUAL( {type.get(t, 0)}, 1 );
  TEST_EQUAL( {type.get(t, 1)}, 0 );
  TEST_EQUAL( {type.get(t, 2)}, 1 );
""")

x.unit(f"{type.set}()/get()/flip(): bit modifications", f"""
  size_t i;
  {type.resize(t, 70)};
  TEST_EQUAL( {type.size(t)}, 70 );
  TEST_TRUE( {type.none(t)} );

  {type.set(t, 0, 1)};
  {type.set(t, 63, 1)};
  {type.set(t, 64, 1)};
  {type.set(t, 69, 1)};

  TEST_EQUAL( {type.get(t, 0)}, 1 );
  TEST_EQUAL( {type.get(t, 63)}, 1 );
  TEST_EQUAL( {type.get(t, 64)}, 1 );
  TEST_EQUAL( {type.get(t, 69)}, 1 );
  TEST_EQUAL( {type.get(t, 1)}, 0 );
  TEST_EQUAL( {type.get(t, 65)}, 0 );
  TEST_EQUAL( {type.count(t)}, 4 );

  {type.clear_bit(t, 63)};
  TEST_EQUAL( {type.get(t, 63)}, 0 );
  TEST_EQUAL( {type.count(t)}, 3 );

  {type.flip_bit(t, 0)};
  TEST_EQUAL( {type.get(t, 0)}, 0 );
  {type.flip_bit(t, 0)};
  TEST_EQUAL( {type.get(t, 0)}, 1 );
""")

x.unit(f"{type.set_all}()/{type.reset_all}(): bulk bit operations", f"""
  {type.resize(t, 100)};
  {type.set_all(t)};
  TEST_EQUAL( {type.count(t)}, 100 );
  TEST_TRUE( {type.all(t)} );
  TEST_TRUE( {type.any(t)} );
  TEST_FALSE( {type.none(t)} );

  {type.reset_all(t)};
  TEST_EQUAL( {type.count(t)}, 0 );
  TEST_FALSE( {type.all(t)} );
  TEST_FALSE( {type.any(t)} );
  TEST_TRUE( {type.none(t)} );

  {type.flip(t)};
  TEST_EQUAL( {type.count(t)}, 100 );
  TEST_TRUE( {type.all(t)} );
""")

x.unit(f"{type.find_first}(): search for set bits", f"""
  {type.resize(t, 80)};
  TEST_EQUAL( {type.find_first(t)}, 80 );

  {type.set(t, 65, 1)};
  TEST_EQUAL( {type.find_first(t)}, 65 );

  {type.set(t, 10, 1)};
  TEST_EQUAL( {type.find_first(t)}, 10 );

  {type.set(t, 0, 1)};
  TEST_EQUAL( {type.find_first(t)}, 0 );
""")

x.unit(f"{type.copy}()/{type.move}(): value semantics", f"""
  {t1.definition};
  {t2.definition};
  {type.create(t1)};
  {type.create(t2)};

  {type.push(t1, 1)};
  {type.push(t1, 0)};
  {type.push(t1, 1)};

  {type.copy(t2, t1)};
  TEST_EQUAL( {type.size(t2)}, 3 );
  TEST_TRUE( {type.equal(t1, t2)} );

  {type.destroy(t2)};
  {type.create(t2)};
  {type.move(t2, t1)};
  TEST_EQUAL( {type.size(t2)}, 3 );
  TEST_EQUAL( {type.size(t1)}, 0 );
  TEST_TRUE( {type.empty(t1)} );

  {type.destroy(t1)};
  {type.destroy(t2)};
""")

x.unit(f"{type.apply_union}(): bitwise union", f"""
  {t1.definition};
  {t2.definition};
  {type.create(t1)};
  {type.create(t2)};

  {type.resize(t1, 10)};
  {type.resize(t2, 10)};
  {type.set(t1, 1, 1)};
  {type.set(t1, 3, 1)};
  {type.set(t2, 3, 1)};
  {type.set(t2, 5, 1)};

  {type.apply_union(t1, t2)};
  TEST_EQUAL( {type.get(t1, 1)}, 1 );
  TEST_EQUAL( {type.get(t1, 3)}, 1 );
  TEST_EQUAL( {type.get(t1, 5)}, 1 );
  TEST_EQUAL( {type.get(t1, 0)}, 0 );
  TEST_EQUAL( {type.count(t1)}, 3 );

  {type.destroy(t1)};
  {type.destroy(t2)};
""")

x.unit(f"{type.apply_intersection}(): bitwise intersection", f"""
  {t1.definition};
  {t2.definition};
  {type.create(t1)};
  {type.create(t2)};

  {type.resize(t1, 10)};
  {type.resize(t2, 10)};
  {type.set(t1, 1, 1)};
  {type.set(t1, 3, 1)};
  {type.set(t2, 3, 1)};
  {type.set(t2, 5, 1)};

  {type.apply_intersection(t1, t2)};
  TEST_EQUAL( {type.get(t1, 1)}, 0 );
  TEST_EQUAL( {type.get(t1, 3)}, 1 );
  TEST_EQUAL( {type.get(t1, 5)}, 0 );
  TEST_EQUAL( {type.count(t1)}, 1 );

  {type.destroy(t1)};
  {type.destroy(t2)};
""")

x.unit(f"{type.apply_difference}(): bitwise difference", f"""
  {t1.definition};
  {t2.definition};
  {type.create(t1)};
  {type.create(t2)};

  {type.resize(t1, 10)};
  {type.resize(t2, 10)};
  {type.set(t1, 1, 1)};
  {type.set(t1, 3, 1)};
  {type.set(t2, 3, 1)};
  {type.set(t2, 5, 1)};

  {type.apply_difference(t1, t2)};
  TEST_EQUAL( {type.get(t1, 1)}, 1 );
  TEST_EQUAL( {type.get(t1, 3)}, 0 );
  TEST_EQUAL( {type.get(t1, 5)}, 0 );
  TEST_EQUAL( {type.count(t1)}, 1 );

  {type.destroy(t1)};
  {type.destroy(t2)};
""")

x.unit(f"{type.apply_symmetric_difference}(): bitwise symmetric difference", f"""
  {t1.definition};
  {t2.definition};
  {type.create(t1)};
  {type.create(t2)};

  {type.resize(t1, 10)};
  {type.resize(t2, 10)};
  {type.set(t1, 1, 1)};
  {type.set(t1, 3, 1)};
  {type.set(t2, 3, 1)};
  {type.set(t2, 5, 1)};

  {type.apply_symmetric_difference(t1, t2)};
  TEST_EQUAL( {type.get(t1, 1)}, 1 );
  TEST_EQUAL( {type.get(t1, 3)}, 0 );
  TEST_EQUAL( {type.get(t1, 5)}, 1 );
  TEST_EQUAL( {type.count(t1)}, 2 );

  {type.destroy(t1)};
  {type.destroy(t2)};
""")

x.unit(f"{type.create_union}(): constructing union from immutable sources", f"""
  {t1.definition};
  {t2.definition};
  {t3.definition};
  {type.create(t1)};
  {type.create(t2)};

  {type.resize(t1, 8)};
  {type.resize(t2, 16)};
  {type.set(t1, 1, 1)};
  {type.set(t1, 3, 1)};
  {type.set(t2, 3, 1)};
  {type.set(t2, 10, 1)};

  {type.create_union(t3, t1, t2)};
  TEST_EQUAL( {type.size(t3)}, 16 );
  TEST_EQUAL( {type.get(t3, 1)}, 1 );
  TEST_EQUAL( {type.get(t3, 3)}, 1 );
  TEST_EQUAL( {type.get(t3, 10)}, 1 );
  TEST_EQUAL( {type.count(t3)}, 3 );

  /* Inputs unmodified */
  TEST_EQUAL( {type.size(t1)}, 8 );
  TEST_EQUAL( {type.count(t1)}, 2 );
  TEST_EQUAL( {type.size(t2)}, 16 );
  TEST_EQUAL( {type.count(t2)}, 2 );

  {type.destroy(t3)};
  {type.destroy(t1)};
  {type.destroy(t2)};
""")

x.unit(f"{type.create_intersection}(): constructing intersection from immutable sources", f"""
  {t1.definition};
  {t2.definition};
  {t3.definition};
  {type.create(t1)};
  {type.create(t2)};

  {type.resize(t1, 8)};
  {type.resize(t2, 16)};
  {type.set(t1, 1, 1)};
  {type.set(t1, 3, 1)};
  {type.set(t2, 3, 1)};
  {type.set(t2, 10, 1)};

  {type.create_intersection(t3, t1, t2)};
  TEST_EQUAL( {type.size(t3)}, 8 );
  TEST_EQUAL( {type.get(t3, 1)}, 0 );
  TEST_EQUAL( {type.get(t3, 3)}, 1 );
  TEST_EQUAL( {type.count(t3)}, 1 );

  /* Inputs unmodified */
  TEST_EQUAL( {type.size(t1)}, 8 );
  TEST_EQUAL( {type.size(t2)}, 16 );

  {type.destroy(t3)};
  {type.destroy(t1)};
  {type.destroy(t2)};
""")

x.unit(f"{type.create_difference}(): constructing difference from immutable sources", f"""
  {t1.definition};
  {t2.definition};
  {t3.definition};
  {type.create(t1)};
  {type.create(t2)};

  {type.resize(t1, 12)};
  {type.resize(t2, 8)};
  {type.set(t1, 1, 1)};
  {type.set(t1, 3, 1)};
  {type.set(t1, 10, 1)};
  {type.set(t2, 3, 1)};

  {type.create_difference(t3, t1, t2)};
  TEST_EQUAL( {type.size(t3)}, 12 );
  TEST_EQUAL( {type.get(t3, 1)}, 1 );
  TEST_EQUAL( {type.get(t3, 3)}, 0 );
  TEST_EQUAL( {type.get(t3, 10)}, 1 );
  TEST_EQUAL( {type.count(t3)}, 2 );

  /* Inputs unmodified */
  TEST_EQUAL( {type.size(t1)}, 12 );
  TEST_EQUAL( {type.size(t2)}, 8 );

  {type.destroy(t3)};
  {type.destroy(t1)};
  {type.destroy(t2)};
""")

x.unit(f"{type.create_symmetric_difference}(): constructing symmetric difference from immutable sources", f"""
  {t1.definition};
  {t2.definition};
  {t3.definition};
  {type.create(t1)};
  {type.create(t2)};

  {type.resize(t1, 8)};
  {type.resize(t2, 16)};
  {type.set(t1, 1, 1)};
  {type.set(t1, 3, 1)};
  {type.set(t2, 3, 1)};
  {type.set(t2, 10, 1)};

  {type.create_symmetric_difference(t3, t1, t2)};
  TEST_EQUAL( {type.size(t3)}, 16 );
  TEST_EQUAL( {type.get(t3, 1)}, 1 );
  TEST_EQUAL( {type.get(t3, 3)}, 0 );
  TEST_EQUAL( {type.get(t3, 10)}, 1 );
  TEST_EQUAL( {type.count(t3)}, 2 );

  /* Inputs unmodified */
  TEST_EQUAL( {type.size(t1)}, 8 );
  TEST_EQUAL( {type.size(t2)}, 16 );

  {type.destroy(t3)};
  {type.destroy(t1)};
  {type.destroy(t2)};
""")

x.unit(f"{type.is_subset}(): subset predicate", f"""
  {t1.definition};
  {t2.definition};
  {type.create(t1)};
  {type.create(t2)};

  {type.resize(t1, 10)};
  {type.resize(t2, 10)};
  TEST_TRUE( {type.is_subset(t1, t2)} );

  {type.set(t1, 2, 1)};
  TEST_FALSE( {type.is_subset(t1, t2)} );

  {type.set(t2, 2, 1)};
  {type.set(t2, 4, 1)};
  TEST_TRUE( {type.is_subset(t1, t2)} );

  {type.destroy(t1)};
  {type.destroy(t2)};
""")
