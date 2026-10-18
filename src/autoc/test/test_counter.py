from autoc.test import *
from autoc.counter import Counter
import autoc.flat_map
import autoc.chained_hash_map

# Test Counter backed by FlatMap
x = Type(type := Counter("flat_int_counter", "int", autoc.flat_map.Map))

t = type.variable("t")
t1 = type.variable("t1")
t2 = type.variable("t2")
r = type.range.variable("r")


x.setup(f"""
  {t.definition};
  {type.create(t)};
""")
x.cleanup(f"""
  {type.destroy(t)};
""")


x.unit(f"{type.empty}(): new counter is empty", f"""
  TEST_TRUE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 0 );
  TEST_EQUAL( {type.total_size(t)}, 0 );
  TEST_EQUAL( {type.distinct_size(t)}, 0 );
""")

x.unit(f"{type.add}(): add elements with multiplicity", f"""
  {type.add(t, 10, 3)};
  TEST_FALSE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 3 );
  TEST_EQUAL( {type.total_size(t)}, 3 );
  TEST_EQUAL( {type.distinct_size(t)}, 1 );
  TEST_EQUAL( {type.count(t, 10)}, 3 );
  TEST_TRUE( {type.contains(t, 10)} );
  TEST_FALSE( {type.contains(t, 20)} );

  {type.add(t, 20, 1)};
  TEST_EQUAL( {type.size(t)}, 4 );
  TEST_EQUAL( {type.distinct_size(t)}, 2 );
  TEST_EQUAL( {type.count(t, 20)}, 1 );

  /* Add more to existing key */
  {type.add(t, 10, 2)};
  TEST_EQUAL( {type.size(t)}, 6 );
  TEST_EQUAL( {type.distinct_size(t)}, 2 );
  TEST_EQUAL( {type.count(t, 10)}, 5 );
""")

x.unit(f"{type.put}()/{type.wipe}(): multiset protocol put and wipe", f"""
  TEST_TRUE( {type.put(t, 50)} );
  TEST_EQUAL( {type.count(t, 50)}, 1 );
  TEST_TRUE( {type.put(t, 50)} );
  TEST_EQUAL( {type.count(t, 50)}, 2 );
  TEST_EQUAL( {type.size(t)}, 2 );
  TEST_EQUAL( {type.wipe(t, 50)}, 2 );
  TEST_EQUAL( {type.count(t, 50)}, 0 );
  TEST_EQUAL( {type.size(t)}, 0 );
""")

x.unit(f"{type.subtract}()/{type.remove}(): partial, single, and complete removal", f"""
  {type.add(t, 10, 5)};
  {type.add(t, 20, 2)};
  TEST_EQUAL( {type.size(t)}, 7 );
  TEST_EQUAL( {type.distinct_size(t)}, 2 );

  /* Partial removal of key 10 via subtract */
  TEST_EQUAL( {type.subtract(t, 10, 2)}, 2 );
  TEST_EQUAL( {type.count(t, 10)}, 3 );
  TEST_EQUAL( {type.size(t)}, 5 );
  TEST_EQUAL( {type.distinct_size(t)}, 2 );

  /* Single removal of key 10 via Multiset remove */
  TEST_TRUE( {type.remove(t, 10)} );
  TEST_EQUAL( {type.count(t, 10)}, 2 );
  TEST_EQUAL( {type.size(t)}, 4 );

  /* Partial removal via remove_count alias */
  TEST_EQUAL( {type.remove_count(t, 10, 1)}, 1 );
  TEST_EQUAL( {type.count(t, 10)}, 1 );

  /* Complete removal of key 20 by exceeding count */
  TEST_EQUAL( {type.subtract(t, 20, 10)}, 2 );
  TEST_EQUAL( {type.count(t, 20)}, 0 );
  TEST_FALSE( {type.contains(t, 20)} );
  TEST_EQUAL( {type.size(t)}, 1 );
  TEST_EQUAL( {type.distinct_size(t)}, 1 );

  /* Remove non-existing element */
  TEST_EQUAL( {type.subtract(t, 999, 1)}, 0 );
  TEST_FALSE( {type.remove(t, 999)} );
""")

x.unit(f"{type.remove_all}(): remove all occurrences of key", f"""
  {type.add(t, 10, 100)};
  {type.add(t, 20, 50)};
  TEST_EQUAL( {type.remove_all(t, 10)}, 100 );
  TEST_EQUAL( {type.count(t, 10)}, 0 );
  TEST_FALSE( {type.contains(t, 10)} );
  TEST_EQUAL( {type.size(t)}, 50 );
  TEST_EQUAL( {type.distinct_size(t)}, 1 );

  /* Remove all on absent key returns 0 */
  TEST_EQUAL( {type.remove_all(t, 10)}, 0 );
""")

x.unit(f"{type.clear}(): clear resets all counts", f"""
  {type.add(t, 1, 10)};
  {type.add(t, 2, 20)};
  {type.clear(t)};
  TEST_TRUE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 0 );
  TEST_EQUAL( {type.distinct_size(t)}, 0 );
  TEST_EQUAL( {type.count(t, 1)}, 0 );
""")

x.unit(f"{type.copy}()/{type.move}(): value semantics", f"""
  {t1.definition};
  {t2.definition};
  {type.create(t1)};
  {type.create(t2)};

  {type.add(t, 10, 3)};
  {type.add(t, 20, 7)};

  {type.copy(t1, t)};
  TEST_EQUAL( {type.size(t1)}, 10 );
  TEST_EQUAL( {type.count(t1, 10)}, 3 );
  TEST_EQUAL( {type.count(t1, 20)}, 7 );
  TEST_TRUE( {type.equal(t, t1)} );

  {type.move(t2, t1)};
  TEST_EQUAL( {type.size(t2)}, 10 );
  TEST_TRUE( {type.empty(t1)} );
  TEST_TRUE( {type.equal(t, t2)} );

  {type.destroy(t1)};
  {type.destroy(t2)};
""")

x.unit(f"{type.range}(): traverse elements and counts in order", f"""
  {r.definition};
  size_t step = 0;

  {type.add(t, 30, 3)};
  {type.add(t, 10, 1)};
  {type.add(t, 20, 2)};

  /* FlatMap backend guarantees ascending element order */
  for({r} = {type.range.new(t)}; !{type.range.empty(r)}; {type.range.move_front(r)}) {{
    if(step == 0) {{
      TEST_EQUAL( *{type.range.front_view(r)}, 10 );
      TEST_EQUAL( {type.range.count(r)}, 1 );
    }} else if(step == 1) {{
      TEST_EQUAL( *{type.range.front_view(r)}, 20 );
      TEST_EQUAL( {type.range.count(r)}, 2 );
    }} else if(step == 2) {{
      TEST_EQUAL( *{type.range.front_view(r)}, 30 );
      TEST_EQUAL( {type.range.count(r)}, 3 );
    }}
    ++step;
  }}
  TEST_EQUAL( step, 3 );
""")

x.unit(f"{type.apply_union}(): multiset union (max counts)", f"""
  {t1.definition};
  {type.create(t1)};

  {type.add(t, 10, 5)};
  {type.add(t, 20, 2)};

  {type.add(t1, 10, 3)};
  {type.add(t1, 20, 6)};
  {type.add(t1, 30, 4)};

  {type.apply_union(t, t1)};
  /* max(5, 3) = 5 for 10; max(2, 6) = 6 for 20; max(0, 4) = 4 for 30 */
  TEST_EQUAL( {type.count(t, 10)}, 5 );
  TEST_EQUAL( {type.count(t, 20)}, 6 );
  TEST_EQUAL( {type.count(t, 30)}, 4 );
  TEST_EQUAL( {type.size(t)}, 15 );
  TEST_EQUAL( {type.distinct_size(t)}, 3 );

  {type.destroy(t1)};
""")

x.unit(f"{type.apply_intersection}(): multiset intersection (min counts)", f"""
  {t1.definition};
  {type.create(t1)};

  {type.add(t, 10, 5)};
  {type.add(t, 20, 2)};
  {type.add(t, 40, 1)};

  {type.add(t1, 10, 3)};
  {type.add(t1, 20, 6)};
  {type.add(t1, 30, 4)};

  {type.apply_intersection(t, t1)};
  /* min(5, 3) = 3 for 10; min(2, 6) = 2 for 20; absent for 40 and 30 */
  TEST_EQUAL( {type.count(t, 10)}, 3 );
  TEST_EQUAL( {type.count(t, 20)}, 2 );
  TEST_EQUAL( {type.count(t, 30)}, 0 );
  TEST_EQUAL( {type.count(t, 40)}, 0 );
  TEST_EQUAL( {type.size(t)}, 5 );
  TEST_EQUAL( {type.distinct_size(t)}, 2 );

  {type.destroy(t1)};
""")

x.unit(f"{type.apply_difference}(): multiset difference", f"""
  {t1.definition};
  {type.create(t1)};

  {type.add(t, 10, 5)};
  {type.add(t, 20, 2)};

  {type.add(t1, 10, 2)};
  {type.add(t1, 20, 5)};

  {type.apply_difference(t, t1)};
  /* 5 - 2 = 3 for 10; max(0, 2 - 5) = 0 for 20 */
  TEST_EQUAL( {type.count(t, 10)}, 3 );
  TEST_EQUAL( {type.count(t, 20)}, 0 );
  TEST_FALSE( {type.contains(t, 20)} );
  TEST_EQUAL( {type.size(t)}, 3 );
  TEST_EQUAL( {type.distinct_size(t)}, 1 );

  {type.destroy(t1)};
""")

x.unit(f"{type.create_union}(): constructing union from immutable sources", f"""
  {t1.definition};
  {t2.definition};
  {type.create(t1)};

  {type.add(t, 10, 5)};
  {type.add(t, 20, 2)};

  {type.add(t1, 10, 3)};
  {type.add(t1, 20, 6)};
  {type.add(t1, 30, 4)};

  {type.create_union(t2, t, t1)};

  TEST_EQUAL( {type.count(t2, 10)}, 5 );
  TEST_EQUAL( {type.count(t2, 20)}, 6 );
  TEST_EQUAL( {type.count(t2, 30)}, 4 );
  TEST_EQUAL( {type.size(t2)}, 15 );
  TEST_EQUAL( {type.distinct_size(t2)}, 3 );

  /* Ensure inputs are unmodified */
  TEST_EQUAL( {type.size(t)}, 7 );
  TEST_EQUAL( {type.size(t1)}, 13 );

  {type.destroy(t2)};
  {type.destroy(t1)};
""")

x.unit(f"{type.create_intersection}(): constructing intersection from immutable sources", f"""
  {t1.definition};
  {t2.definition};
  {type.create(t1)};

  {type.add(t, 10, 5)};
  {type.add(t, 20, 2)};
  {type.add(t, 40, 1)};

  {type.add(t1, 10, 3)};
  {type.add(t1, 20, 6)};
  {type.add(t1, 30, 4)};

  {type.create_intersection(t2, t, t1)};

  TEST_EQUAL( {type.count(t2, 10)}, 3 );
  TEST_EQUAL( {type.count(t2, 20)}, 2 );
  TEST_EQUAL( {type.count(t2, 30)}, 0 );
  TEST_EQUAL( {type.count(t2, 40)}, 0 );
  TEST_EQUAL( {type.size(t2)}, 5 );
  TEST_EQUAL( {type.distinct_size(t2)}, 2 );

  /* Ensure inputs are unmodified */
  TEST_EQUAL( {type.size(t)}, 8 );
  TEST_EQUAL( {type.size(t1)}, 13 );

  {type.destroy(t2)};
  {type.destroy(t1)};
""")

x.unit(f"{type.create_difference}(): constructing difference from immutable sources", f"""
  {t1.definition};
  {t2.definition};
  {type.create(t1)};

  {type.add(t, 10, 5)};
  {type.add(t, 20, 2)};

  {type.add(t1, 10, 2)};
  {type.add(t1, 20, 5)};

  {type.create_difference(t2, t, t1)};

  TEST_EQUAL( {type.count(t2, 10)}, 3 );
  TEST_EQUAL( {type.count(t2, 20)}, 0 );
  TEST_FALSE( {type.contains(t2, 20)} );
  TEST_EQUAL( {type.size(t2)}, 3 );
  TEST_EQUAL( {type.distinct_size(t2)}, 1 );

  /* Ensure inputs are unmodified */
  TEST_EQUAL( {type.size(t)}, 7 );
  TEST_EQUAL( {type.size(t1)}, 7 );

  {type.destroy(t2)};
  {type.destroy(t1)};
""")

x.unit(f"{type.is_subset}(): sub-multiset test", f"""
  {t1.definition};
  {type.create(t1)};

  {type.add(t, 10, 2)};
  {type.add(t, 20, 3)};

  {type.add(t1, 10, 2)};
  {type.add(t1, 20, 5)};
  {type.add(t1, 30, 1)};

  TEST_TRUE( {type.is_subset(t, t1)} );
  TEST_FALSE( {type.is_subset(t1, t)} );

  /* Equal counts is still a subset */
  TEST_TRUE( {type.is_subset(t, t)} );

  /* Exceeding count in target makes it not a subset */
  {type.add(t, 10, 1)}; /* t now has 10: 3, t1 has 10: 2 */
  TEST_FALSE( {type.is_subset(t, t1)} );

  {type.destroy(t1)};
""")


x.unit(f"{type.equal_range}(): get range spanning element occurrences", f"""
  {r.definition};
  {type.add(t, 25, 4)};

  {r} = {type.equal_range(t, 25)};
  TEST_FALSE( {type.range.empty(r)} );
  TEST_EQUAL( *{type.range.front_view(r)}, 25 );
  TEST_EQUAL( {type.range.count(r)}, 4 );
  {type.range.move_front(r)};
  TEST_TRUE( {type.range.empty(r)} );

  /* Absent element yields empty range */
  {r} = {type.equal_range(t, 999)};
  TEST_TRUE( {type.range.empty(r)} );
""")


# Also test Counter backed by ChainedHashMap
x_hash = Type(type_h := Counter("hash_int_counter", "int", autoc.chained_hash_map.Map))
th = type_h.variable("th")

x_hash.setup(f"""
  {th.definition};
  {type_h.create(th)};
""")
x_hash.cleanup(f"""
  {type_h.destroy(th)};
""")

x_hash.unit(f"{type_h}: operates with ChainedHashMap backend", f"""
  {type_h.add(th, 100, 5)};
  {type_h.add(th, 200, 10)};
  TEST_EQUAL( {type_h.size(th)}, 15 );
  TEST_EQUAL( {type_h.distinct_size(th)}, 2 );
  TEST_EQUAL( {type_h.count(th, 100)}, 5 );
  TEST_EQUAL( {type_h.count(th, 200)}, 10 );
  TEST_EQUAL( {type_h.subtract(th, 100, 3)}, 3 );
  TEST_EQUAL( {type_h.count(th, 100)}, 2 );
  TEST_TRUE( {type_h.remove(th, 100)} );
  TEST_EQUAL( {type_h.count(th, 100)}, 1 );
  TEST_EQUAL( {type_h.wipe(th, 200)}, 10 );
  TEST_EQUAL( {type_h.size(th)}, 1 );
  TEST_EQUAL( {type_h.distinct_size(th)}, 1 );
""")
