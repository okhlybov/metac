from autoc.test import *
from autoc.flat_set import Set

x = Type(type := Set("int_flat_set", "int"))

t = type.variable("t")
range = type.range
r = range.variable("r")

x.setup(f"""
  {t.definition};
""")
x.cleanup(f"""
  {type.destroy(t)};
""")

x.unit(f"{type.create}(): create empty set", f"""
  {type.create(t)};
  TEST_TRUE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 0 );
  TEST_EQUAL( {type.capacity(t)}, 0 );
""")

x.unit(f"{type.put}(): put new element into empty set", f"""
  {type.create(t)};
  TEST_TRUE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 0 );
  TEST_TRUE( {type.put(t, 10)} );
  TEST_FALSE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 1 );
  TEST_TRUE( {type.capacity(t)} >= 1 );
""")

x.unit(f"{type.put}(): put duplicate element", f"""
  {type.create(t)};
  TEST_TRUE( {type.put(t, 10)} );
  TEST_FALSE( {type.put(t, 10)} );
  TEST_EQUAL( {type.size(t)}, 1 );
""")

x.unit(f"{type.put}(): elements kept in sorted order", f"""
  {type.create(t)};
  TEST_TRUE( {type.put(t, 30)} );
  TEST_TRUE( {type.put(t, 10)} );
  TEST_TRUE( {type.put(t, 20)} );
  TEST_EQUAL( {type.size(t)}, 3 );
  TEST_EQUAL( {type.data(t)}[0], 10 );
  TEST_EQUAL( {type.data(t)}[1], 20 );
  TEST_EQUAL( {type.data(t)}[2], 30 );
""")

x.unit(f"{type.remove}(): remove absent element", f"""
  {type.create(t)};
  TEST_FALSE( {type.remove(t, 10)} );
""")

x.unit(f"{type.remove}(): remove elements from various positions", f"""
  {type.create(t)};
  {type.put(t, 10)};
  {type.put(t, 20)};
  {type.put(t, 30)};
  TEST_TRUE( {type.remove(t, 20)} ); /* middle */
  TEST_EQUAL( {type.size(t)}, 2 );
  TEST_EQUAL( {type.data(t)}[0], 10 );
  TEST_EQUAL( {type.data(t)}[1], 30 );
  TEST_TRUE( {type.remove(t, 10)} ); /* first */
  TEST_EQUAL( {type.size(t)}, 1 );
  TEST_EQUAL( {type.data(t)}[0], 30 );
  TEST_TRUE( {type.remove(t, 30)} ); /* last */
  TEST_EQUAL( {type.size(t)}, 0 );
  TEST_TRUE( {type.empty(t)} );
""")

x.unit(f"{type.reserve}/{type.compact}(): reserve and compact capacity", f"""
  {type.create(t)};
  {type.reserve(t, 100)};
  TEST_TRUE( {type.capacity(t)} >= 100 );
  TEST_EQUAL( {type.size(t)}, 0 );
  {type.put(t, 5)};
  {type.put(t, 15)};
  {type.compact(t)};
  TEST_EQUAL( {type.size(t)}, 2 );
  TEST_EQUAL( {type.capacity(t)}, 2 );
""")

x.unit(f"{type.contains}(): test binary search containment", f"""
  {type.create(t)};
  TEST_FALSE( {type.contains(t, 10)} );
  {type.put(t, 10)};
  {type.put(t, 20)};
  {type.put(t, 30)};
  TEST_TRUE( {type.contains(t, 10)} );
  TEST_TRUE( {type.contains(t, 20)} );
  TEST_TRUE( {type.contains(t, 30)} );
  TEST_FALSE( {type.contains(t, 5)} );
  TEST_FALSE( {type.contains(t, 25)} );
  TEST_FALSE( {type.contains(t, 35)} );
""")

x.unit(f"{type.find_view}(): find view of element", f"""
  {type.create(t)};
  TEST_NULL( {type.find_view(t, 10)} );
  {type.put(t, 10)};
  {type.put(t, 20)};
  TEST_NOT_NULL( {type.find_view(t, 10)} );
  TEST_EQUAL( *{type.find_view(t, 10)}, 10 );
  TEST_NOT_NULL( {type.find_view(t, 20)} );
  TEST_EQUAL( *{type.find_view(t, 20)}, 20 );
  TEST_NULL( {type.find_view(t, 30)} );
""")

x.unit(f"{type.lower_bound}/{type.upper_bound}/{type.binary_search}(): bounds and search", f"""
  {type.create(t)};
  {type.put(t, 10)};
  {type.put(t, 20)};
  {type.put(t, 30)};
  TEST_EQUAL( {type.lower_bound(t, 5)}, 0 );
  TEST_EQUAL( {type.lower_bound(t, 10)}, 0 );
  TEST_EQUAL( {type.lower_bound(t, 15)}, 1 );
  TEST_EQUAL( {type.lower_bound(t, 20)}, 1 );
  TEST_EQUAL( {type.lower_bound(t, 25)}, 2 );
  TEST_EQUAL( {type.lower_bound(t, 30)}, 2 );
  TEST_EQUAL( {type.lower_bound(t, 35)}, 3 );
  TEST_EQUAL( {type.upper_bound(t, 5)}, 0 );
  TEST_EQUAL( {type.upper_bound(t, 10)}, 1 );
  TEST_EQUAL( {type.upper_bound(t, 15)}, 1 );
  TEST_EQUAL( {type.upper_bound(t, 20)}, 2 );
  TEST_EQUAL( {type.upper_bound(t, 30)}, 3 );
  TEST_TRUE( {type.binary_search(t, 20)} );
  TEST_FALSE( {type.binary_search(t, 25)} );
""")

x.unit(f"{type.equal}/{type.compare}(): compare and equality", f"""
  {type.create(t)};
  {{
    {type.variable("other").definition};
    {type.create("&other")};
    TEST_TRUE( {type.equal(t, "&other")} );
    TEST_EQUAL( {type.compare(t, "&other")}, 0 );
    {type.put(t, 1)};
    {type.put(t, 2)};
    TEST_FALSE( {type.equal(t, "&other")} );
    TEST_TRUE( {type.compare(t, "&other")} > 0 );
    {type.put("&other", 1)};
    {type.put("&other", 2)};
    TEST_TRUE( {type.equal(t, "&other")} );
    TEST_EQUAL( {type.compare(t, "&other")}, 0 );
    {type.destroy("&other")};
  }}
""")

x.unit(f"{type.copy}/{type.move}(): copy and move", f"""
  {type.create(t)};
  {type.put(t, 10)};
  {type.put(t, 20)};
  {{
    {type.variable("cp").definition};
    {type.variable("mv").definition};
    {type.copy("&cp", t)};
    TEST_EQUAL( {type.size("&cp")}, 2 );
    TEST_TRUE( {type.equal(t, "&cp")} );
    {type.move("&mv", "&cp")};
    TEST_EQUAL( {type.size("&mv")}, 2 );
    TEST_EQUAL( {type.size("&cp")}, 0 );
    TEST_TRUE( {type.equal(t, "&mv")} );
    {type.destroy("&cp")};
    {type.destroy("&mv")};
  }}
""")

x.unit(f"{type.range}(): DirectAccess range iteration", f"""
  {type.create(t)};
  {type.put(t, 10)};
  {type.put(t, 20)};
  {type.put(t, 30)};
  {{
    {r.definition};
    int sum = 0;
    for({r} = {range.new(t)}; !{range.empty(r)}; {range.move_front(r)}) {{
      sum += {range.front(r)};
    }}
    TEST_EQUAL( sum, 60 );
    {r} = {range.new(t)};
    TEST_EQUAL( {range.size(r)}, 3 );
    TEST_EQUAL( {range.get(r, 0)}, 10 );
    TEST_EQUAL( {range.get(r, 1)}, 20 );
    TEST_EQUAL( {range.get(r, 2)}, 30 );
    TEST_EQUAL( {range.back(r)}, 30 );
    {range.move_back(r)};
    TEST_EQUAL( {range.back(r)}, 20 );
  }}
""")

x.unit("algebraic operations: union, intersection, difference", f"""
  {type.create(t)};
  {type.put(t, 1)};
  {type.put(t, 2)};
  {type.put(t, 3)};
  {{
    {type.variable("b").definition};
    {type.create("&b")};
    {type.put("&b", 2)};
    {type.put("&b", 3)};
    {type.put("&b", 4)};
    TEST_TRUE( {type.is_subset("&b", t)} == 0 );
    TEST_TRUE( {type.apply_union(t, "&b")} == 1 ); /* adds 4 */
    TEST_EQUAL( {type.size(t)}, 4 );
    TEST_TRUE( {type.contains(t, 4)} );
    TEST_TRUE( {type.is_superset(t, "&b")} );
    TEST_TRUE( {type.apply_difference(t, "&b")} == 3 ); /* removes 2, 3, 4 */
    TEST_EQUAL( {type.size(t)}, 1 );
    TEST_TRUE( {type.contains(t, 1)} );
    {type.destroy("&b")};
  }}
""")

x.unit("symmetric difference and self algebra", f"""
  {type.create(t)};
  {type.put(t, 1)};
  {type.put(t, 2)};
  {{
    {type.variable("b").definition};
    {type.create("&b")};
    {type.put("&b", 2)};
    {type.put("&b", 3)};
    TEST_EQUAL( {type.apply_symmetric_difference(t, "&b")}, 2 ); /* removes 2, adds 3 -> {1, 3} */
    TEST_EQUAL( {type.size(t)}, 2 );
    TEST_TRUE( {type.contains(t, 1)} );
    TEST_FALSE( {type.contains(t, 2)} );
    TEST_TRUE( {type.contains(t, 3)} );
    /* Self-union is a no-op */
    TEST_EQUAL( {type.apply_union(t, t)}, 0 );
    /* Self-intersection removes nothing */
    TEST_EQUAL( {type.apply_intersection(t, t)}, 0 );
    /* Self-difference empties the set */
    TEST_EQUAL( {type.apply_difference(t, t)}, 2 );
    TEST_TRUE( {type.empty(t)} );
    {type.destroy("&b")};
  }}
""")

put_expr = "(i * 37) % 100"
i_expr = "i"

x.unit("churn: repeated put and remove maintains integrity and order", f"""
  int i;
  {type.create(t)};
  for(i = 0; i < 100; ++i) {{
    TEST_TRUE( {type.put(t, put_expr)} );
  }}
  TEST_EQUAL( {type.size(t)}, 100 );
  /* verify sorted order */
  for(i = 0; i < 99; ++i) {{
    TEST_TRUE( {type.data(t)}[i] < {type.data(t)}[i + 1] );
  }}
  /* remove odd numbers */
  for(i = 1; i < 100; i += 2) {{
    TEST_TRUE( {type.remove(t, i_expr)} );
  }}
  TEST_EQUAL( {type.size(t)}, 50 );
  for(i = 0; i < 100; ++i) {{
    if(i % 2 == 0) TEST_TRUE( {type.contains(t, i_expr)} );
    else TEST_FALSE( {type.contains(t, i_expr)} );
  }}
  /* remove remaining */
  for(i = 0; i < 100; i += 2) {{
    TEST_TRUE( {type.remove(t, i_expr)} );
  }}
  TEST_TRUE( {type.empty(t)} );
""")

x.unit(f"{type.count}/{type.equal_range}(): single-element set operations", f"""
  {type.create(t)};
  TEST_EQUAL( {type.count(t, 10)}, 0 );
  {type.put(t, 10)};
  {type.put(t, 20)};
  TEST_EQUAL( {type.count(t, 10)}, 1 );
  TEST_EQUAL( {type.count(t, 20)}, 1 );
  TEST_EQUAL( {type.count(t, 30)}, 0 );

  {{
    {range} eq = {type.equal_range(t, 10)};
    TEST_FALSE( {range.empty("&eq")} );
    TEST_EQUAL( {range.size("&eq")}, 1 );
    TEST_EQUAL( {range.front("&eq")}, 10 );
  }}
  {{
    {range} eq = {type.equal_range(t, 99)};
    TEST_TRUE( {range.empty("&eq")} );
    TEST_EQUAL( {range.size("&eq")}, 0 );
  }}
""")


