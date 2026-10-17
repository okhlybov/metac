from autoc.test import *
from autoc.flat_multiset import Set as Multiset

x = Type(type := Multiset("int_flat_multiset", "int"))

t = type.variable("t")
range = type.range
r = range.variable("r")

x.setup(f"""
  {t.definition};
""")
x.cleanup(f"""
  {type.destroy(t)};
""")

x.unit(f"{type.create}(): create empty multiset", f"""
  {type.create(t)};
  TEST_TRUE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 0 );
  TEST_EQUAL( {type.capacity(t)}, 0 );
""")

x.unit(f"{type.put}(): duplicate elements allowed and sorted", f"""
  {type.create(t)};
  TEST_TRUE( {type.put(t, 30)} );
  TEST_TRUE( {type.put(t, 10)} );
  TEST_TRUE( {type.put(t, 20)} );
  TEST_TRUE( {type.put(t, 10)} );
  TEST_TRUE( {type.put(t, 30)} );
  TEST_TRUE( {type.put(t, 20)} );
  TEST_EQUAL( {type.size(t)}, 6 );
  TEST_FALSE( {type.empty(t)} );

  /* elements must be kept in sorted order with duplicates grouped */
  TEST_EQUAL( {type.data(t)}[0], 10 );
  TEST_EQUAL( {type.data(t)}[1], 10 );
  TEST_EQUAL( {type.data(t)}[2], 20 );
  TEST_EQUAL( {type.data(t)}[3], 20 );
  TEST_EQUAL( {type.data(t)}[4], 30 );
  TEST_EQUAL( {type.data(t)}[5], 30 );
""")

x.unit(f"{type.count}/{type.contains}(): query multiplicity", f"""
  {type.create(t)};
  TEST_EQUAL( {type.count(t, 10)}, 0 );
  TEST_FALSE( {type.contains(t, 10)} );

  {type.put(t, 10)};
  {type.put(t, 20)};
  {type.put(t, 10)};
  {type.put(t, 10)};

  TEST_EQUAL( {type.count(t, 10)}, 3 );
  TEST_EQUAL( {type.count(t, 20)}, 1 );
  TEST_EQUAL( {type.count(t, 30)}, 0 );
  TEST_TRUE( {type.contains(t, 10)} );
  TEST_TRUE( {type.contains(t, 20)} );
  TEST_FALSE( {type.contains(t, 30)} );
""")

x.unit(f"{type.find_view}(): find view to first matching duplicate", f"""
  const int* view;
  {type.create(t)};
  view = {type.find_view(t, 10)};
  TEST_TRUE( view == NULL );

  {type.put(t, 10)};
  {type.put(t, 10)};
  {type.put(t, 20)};
  view = {type.find_view(t, 10)};
  TEST_TRUE( view != NULL );
  TEST_EQUAL( *view, 10 );
  TEST_TRUE( view == &{type.data(t)}[0] );
""")

x.unit(f"{type.equal_range}(): get range spanning all duplicate instances", f"""
  {type.create(t)};
  {type.put(t, 10)};
  {type.put(t, 20)};
  {type.put(t, 20)};
  {type.put(t, 20)};
  {type.put(t, 30)};

  {{
    int c = 0;
    {range} eq = {type.equal_range(t, 20)};
    TEST_FALSE( {range.empty("&eq")} );
    TEST_EQUAL( {range.size("&eq")}, 3 );
    while(!{range.empty("&eq")}) {{
      TEST_EQUAL( {range.front("&eq")}, 20 );
      ++c;
      {range.move_front("&eq")};
    }}
    TEST_EQUAL( c, 3 );
  }}

  {{
    {range} eq = {type.equal_range(t, 99)};
    TEST_TRUE( {range.empty("&eq")} );
    TEST_EQUAL( {range.size("&eq")}, 0 );
  }}
""")

x.unit(f"{type.remove}(): remove single occurrence of element", f"""
  {type.create(t)};
  {type.put(t, 10)};
  {type.put(t, 20)};
  {type.put(t, 20)};
  {type.put(t, 30)};
  TEST_EQUAL( {type.size(t)}, 4 );

  TEST_FALSE( {type.remove(t, 99)} );
  TEST_EQUAL( {type.size(t)}, 4 );

  TEST_TRUE( {type.remove(t, 20)} );
  TEST_EQUAL( {type.size(t)}, 3 );
  TEST_EQUAL( {type.count(t, 20)}, 1 );

  TEST_TRUE( {type.remove(t, 20)} );
  TEST_EQUAL( {type.size(t)}, 2 );
  TEST_EQUAL( {type.count(t, 20)}, 0 );

  TEST_FALSE( {type.remove(t, 20)} );
  TEST_EQUAL( {type.size(t)}, 2 );
""")

x.unit(f"{type.wipe}(): wipe all occurrences of element", f"""
  {type.create(t)};
  {type.put(t, 10)};
  {type.put(t, 10)};
  {type.put(t, 20)};
  {type.put(t, 20)};
  {type.put(t, 20)};
  {type.put(t, 30)};
  TEST_EQUAL( {type.size(t)}, 6 );

  /* Absent element */
  TEST_EQUAL( {type.wipe(t, 99)}, 0 );
  TEST_EQUAL( {type.size(t)}, 6 );

  /* Wipe middle: three 20s */
  TEST_EQUAL( {type.wipe(t, 20)}, 3 );
  TEST_EQUAL( {type.size(t)}, 3 );
  TEST_EQUAL( {type.count(t, 20)}, 0 );
  TEST_EQUAL( {type.data(t)}[0], 10 );
  TEST_EQUAL( {type.data(t)}[1], 10 );
  TEST_EQUAL( {type.data(t)}[2], 30 );

  /* Wipe first: two 10s */
  TEST_EQUAL( {type.wipe(t, 10)}, 2 );
  TEST_EQUAL( {type.size(t)}, 1 );
  TEST_EQUAL( {type.count(t, 10)}, 0 );
  TEST_EQUAL( {type.data(t)}[0], 30 );

  /* Wipe last remaining: one 30 */
  TEST_EQUAL( {type.wipe(t, 30)}, 1 );
  TEST_TRUE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 0 );
""")

x.unit("value semantics: copy, equal, compare, hash", f"""
  {type} other;
  {type.create("&other")};
  {type.create(t)};

  {type.put(t, 10)};
  {type.put(t, 10)};
  {type.put(t, 20)};

  {type.copy("&other", t)};
  TEST_EQUAL( {type.size("&other")}, 3 );
  TEST_TRUE( {type.equal(t, "&other")} );
  TEST_EQUAL( {type.compare(t, "&other")}, 0 );
  TEST_EQUAL( {type.hash(t)}, {type.hash("&other")} );

  /* Adding another element breaks equality */
  {type.put("&other", 10)};
  TEST_FALSE( {type.equal(t, "&other")} );

  {type.destroy("&other")};
""")

x.unit("multialgebraic operations: union, intersection, difference, symmetric_difference, is_subset", f"""
  {type} other;
  {type.create("&other")};
  {type.create(t)};

  /* union: max multiplicities */
  {type.put(t, 10)};
  {type.put(t, 10)};
  {type.put(t, 20)}; /* t: [10, 10, 20] */

  {type.put("&other", 10)};
  {type.put("&other", 20)};
  {type.put("&other", 20)};
  {type.put("&other", 30)}; /* other: [10, 20, 20, 30] */

  TEST_EQUAL( {type.apply_union(t, "&other")}, 2 );
  TEST_EQUAL( {type.size(t)}, 5 );
  TEST_EQUAL( {type.count(t, 10)}, 2 );
  TEST_EQUAL( {type.count(t, 20)}, 2 );
  TEST_EQUAL( {type.count(t, 30)}, 1 );

  /* is_subset / is_superset */
  TEST_TRUE( {type.is_subset("&other", t)} );
  TEST_TRUE( {type.is_superset(t, "&other")} );
  TEST_FALSE( {type.is_subset(t, "&other")} );

  /* intersection: min multiplicities */
  /* t: [10, 10, 20, 20, 30], other: [10, 20, 20, 30] */
  TEST_EQUAL( {type.apply_intersection(t, "&other")}, 1 ); /* one 10 removed */
  TEST_EQUAL( {type.size(t)}, 4 );
  TEST_EQUAL( {type.count(t, 10)}, 1 );
  TEST_EQUAL( {type.count(t, 20)}, 2 );
  TEST_EQUAL( {type.count(t, 30)}, 1 );

  /* difference: subtract multiplicities */
  /* t: [10, 20, 20, 30], other: [10, 20, 20, 30] -> self-difference clears */
  TEST_EQUAL( {type.apply_difference(t, t)}, 4 );
  TEST_EQUAL( {type.size(t)}, 0 );

  /* difference with distinct elements */
  {type.put(t, 10)};
  {type.put(t, 10)};
  {type.put(t, 10)};
  {type.put(t, 20)};
  {type.put(t, 30)}; /* t: [10, 10, 10, 20, 30] */

  TEST_EQUAL( {type.apply_difference(t, "&other")}, 3 ); /* two 10s and one 20 subtracted */
  TEST_EQUAL( {type.size(t)}, 2 );
  TEST_EQUAL( {type.count(t, 10)}, 2 );
  TEST_EQUAL( {type.count(t, 20)}, 0 );
  TEST_EQUAL( {type.count(t, 30)}, 0 );

  /* symmetric_difference */
  {type.destroy(t)};
  {type.create(t)};
  {type.put(t, 10)};
  {type.put(t, 10)};
  {type.put(t, 20)}; /* t: [10, 10, 20] */
  /* other: [10, 20, 20, 30] */
  /* sym_diff: |2-1| 10s = 1, |1-2| 20s = 1, |0-1| 30s = 1 -> [10, 20, 30], 2 removed + 2 added = 4 changed */
  TEST_EQUAL( {type.apply_symmetric_difference(t, "&other")}, 4 );
  TEST_EQUAL( {type.size(t)}, 3 );
  TEST_EQUAL( {type.count(t, 10)}, 1 );
  TEST_EQUAL( {type.count(t, 20)}, 1 );
  TEST_EQUAL( {type.count(t, 30)}, 1 );

  {type.destroy("&other")};
""")

