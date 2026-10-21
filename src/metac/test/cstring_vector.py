from metac.test import *
from metac.vector import Vector
from metac.test.cstring import cstring, s


x = Type(type := Vector("cstring_vector", cstring))

t = type.variable("t")


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

x.unit(f"{type.hash}(): hash empty vector", f"""
  TEST_TRUE( {type.empty(t)} );
  {type.hash(t)};
""")


x.setup(f"""
  {t.definition};
  {type.create_size(t, 10)};
""")
x.cleanup(f"""
  {type.destroy(t)};
""")

x.unit(f"{type.empty}(): test !empty vector", f"""
  TEST_FALSE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 10 );
""")

x.unit(f"{type.hash}(): hash !empty default initialized vector", f"""
  TEST_FALSE( {type.empty(t)} );
  {type.hash(t)};
""")

x.unit(f"{type.hash}(): set element of vector", f"""
  TEST_FALSE( {type.empty(t)} );
  {type.set(t, 0, s("Zzz"))};
""")

x.unit(f"{type.hash}(): contains string", f"""
  TEST_FALSE( {type.empty(t)} );
  {type.set(t, 0, s("Abc"))};
  {type.set(t, 3, s("abC"))};
  TEST_TRUE( {type.contains(t, s("abC"))});
  TEST_FALSE( {type.contains(t, s("abc"))});
""")

x.setup(f"""
  {t.definition};
  {type.create_size(t, 4)};
""")
x.cleanup(f"""
  {type.destroy(t)};
""")

x.unit(f"{type.sort}(): sort strings", f"""
  {type.set(t, 0, s("pear"))};
  {type.set(t, 1, s("apple"))};
  {type.set(t, 2, s("orange"))};
  {type.set(t, 3, s("banana"))};
  {type.sort(t)};
  TEST_TRUE( {type.sorted(t)} );
  TEST_EQUAL_CHARS( {type.view(t, 0)}, {s("apple")} );
  TEST_EQUAL_CHARS( {type.view(t, 1)}, {s("banana")} );
  TEST_EQUAL_CHARS( {type.view(t, 2)}, {s("orange")} );
  TEST_EQUAL_CHARS( {type.view(t, 3)}, {s("pear")} );
""")

x.unit(f"{type.sort}(): sort reverse sorted strings", f"""
  {type.set(t, 0, s("d"))};
  {type.set(t, 1, s("c"))};
  {type.set(t, 2, s("b"))};
  {type.set(t, 3, s("a"))};
  {type.sort(t)};
  TEST_TRUE( {type.sorted(t)} );
  TEST_EQUAL_CHARS( {type.view(t, 0)}, {s("a")} );
""")


x.unit(f"{type.reverse}(): reverse strings", f"""
  {type.set(t, 0, s("d"))};
  {type.set(t, 1, s("c"))};
  {type.set(t, 2, s("b"))};
  {type.set(t, 3, s("a"))};
  {type.reverse(t)};
  TEST_TRUE( {type.sorted(t)} );
  TEST_EQUAL_CHARS( {type.view(t, 0)}, {s("a")} );
""")
