from metac.test import *
from metac.tiered_vector import Vector

# The small chunk shift exercises the multi chunk growth and the chunk table
# doubling without the large element counts

x = Type(type := Vector("int_tiered_vector", "int", chunk_shift=4))

t = type.variable("t")
t2 = type.variable("t2")

range = type.range
r = range.variable("r")


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

x.unit(f"{type.push}(): push into empty vector", f"""
  {type.push(t, 42)};
  TEST_FALSE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 1 );
  TEST_EQUAL( {type.get(t, 0)}, 42 );
""")

x.unit(f"{type.push}(): push across the chunk boundaries", f"""
  int i;
  for(i = 0; i < 100; ++i) {type.push(t, "i")};
  TEST_EQUAL( {type.size(t)}, 100 );
  for(i = 0; i < 100; ++i) TEST_EQUAL( {type.get(t, "i")}, i );
""")

x.unit(f"{type.pop}(): pop the last element", f"""
  {type.push(t, 7)};
  {type.push(t, 9)};
  TEST_EQUAL( {type.pop(t)}, 9 );
  TEST_EQUAL( {type.size(t)}, 1 );
  TEST_EQUAL( {type.get(t, 0)}, 7 );
""")


x.setup(f"""
  int i;
  {t.definition};
  {type.create_size(t, 40)};
""")
x.cleanup(f"""
  {type.destroy(t)};
""")

x.unit(f"{type.create_size}(): default initialized elements", f"""
  TEST_EQUAL( {type.size(t)}, 40 );
  for(i = 0; i < 40; ++i) TEST_EQUAL( {type.get(t, "i")}, 0 );
""")

x.unit(f"{type.set}(): overwrite elements across chunks", f"""
  for(i = 0; i < 40; ++i) {type.set(t, "i", "40 - i")};
  for(i = 0; i < 40; ++i) TEST_EQUAL( {type.get(t, "i")}, 40 - i );
""")

x.unit(f"{type.hash}(): hash !empty vector", f"""
  {type.hash(t)};
""")


x.setup(f"""
  int i;
  {t.definition};
  {t2.definition};
  {type.create(t)};
  {type.create(t2)};
""")
x.cleanup(f"""
  {type.destroy(t)};
  {type.destroy(t2)};
""")

x.unit(f"{type.copy}(): copy across chunks", f"""
  for(i = 0; i < 40; ++i) {type.push(t, "i")};
  {type.copy(t2, t)};
  TEST_TRUE( {type.equal(t, t2)} );
  TEST_EQUAL( {type.hash(t)}, {type.hash(t2)} );
  TEST_EQUAL( {type.size(t2)}, 40 );
  TEST_EQUAL( {type.get(t2, 33)}, 33 );
""")

x.unit(f"{type.equal}(): compare !equal vectors", f"""
  {type.push(t, 1)};
  {type.push(t2, 2)};
  TEST_FALSE( {type.equal(t, t2)} );
""")


x.setup(f"""
  int i;
  {r.definition};
  {t.definition};
  {type.create(t)};
""")
x.cleanup(f"""
  {type.destroy(t)};
""")

x.unit(f"{range}(): traverse empty vector", f"""
  for({r} = {range.new(t)}; !{range.empty(r)}; {range.move_front(r)}) {{
    TEST_FALSE( {range.empty(r)} );
  }}
  TEST_TRUE( {range.empty(r)} );
""")

x.unit(f"{range}(): traverse across chunks", f"""
  i = 0;
  for(i = 0; i < 50; ++i) {type.push(t, "i")};
  i = 0;
  for({r} = {range.new(t)}; !{range.empty(r)}; {range.move_front(r)}) {{
    TEST_EQUAL( {range.front(r)}, i );
    ++i;
  }}
  TEST_EQUAL( i, 50 );
""")


x.unit(f"{range}(): traverse across chunks backward", f"""
  for(i = 0; i < 50; ++i) {type.push(t, "i")};
  i = 50;
  for({r} = {range.new(t)}; !{range.empty(r)}; {range.move_back(r)}) {{
    --i;
    TEST_EQUAL( {range.back(r)}, i );
  }}
  TEST_EQUAL( i, 0 );
""")

x.unit(f"{range}(): direct access by offset and range size", f"""
  for(i = 0; i < 50; ++i) {type.push(t, "i")};
  {r} = {range.new(t)};
  TEST_EQUAL( {range.size(r)}, 50 );
  TEST_EQUAL( {range.get(r, 0)}, 0 );
  TEST_EQUAL( {range.get(r, 16)}, 16 ); /* the offset crossing the chunk boundary */
  TEST_EQUAL( *{range.view(r, 49)}, 49 );
  TEST_EQUAL( {range.front(r)}, {range.get(r, 0)} );
""")


x.unit(f"{type.sort}(): sort across chunks", f"""
  for(i = 0; i < 100; ++i) {type.push(t, "(i*37 + 11)%100")};
  {type.sort(t)};
  TEST_TRUE( {type.sorted(t)} );
  for(i = 0; i < 100; ++i) TEST_EQUAL( {type.get(t, "i")}, i );
""")

x.unit(f"{type.sort}(): sort already sorted and reverse sorted", f"""
  {type.destroy(t)};
  {type.create_size(t, 40)};
  for(i = 0; i < 40; ++i) {type.set(t, "i", "i")};
  {type.sort(t)};
  TEST_TRUE( {type.sorted(t)} );
  {type.reverse(t)};
  TEST_FALSE( {type.sorted(t)} );
  {type.sort(t)};
  TEST_TRUE( {type.sorted(t)} );
  for(i = 0; i < 40; ++i) TEST_EQUAL( {type.get(t, "i")}, i );
""")

x.unit(f"{type.reverse}(): reverse twice restores", f"""
  {type.destroy(t)};
  {type.create_size(t, 40)};
  for(i = 0; i < 40; ++i) {type.set(t, "i", "(i*7)%40")};
  {type.reverse(t)};
  {type.reverse(t)};
  for(i = 0; i < 40; ++i) TEST_EQUAL( {type.get(t, "i")}, (i*7)%40 );
""")

x.unit(f"{type.binary_search}(), {type.lower_bound}(), {type.upper_bound}(): binary search on tiered vector", f"""
  {type.destroy(t)};
  {type.create_size(t, 50)};
  for(i = 0; i < 50; ++i) {type.set(t, "i", "i * 2")};
  /* elements are 0, 2, 4, ..., 98 */
  TEST_TRUE( {type.binary_search(t, 20)} );
  TEST_TRUE( {type.binary_search(t, 0)} );
  TEST_TRUE( {type.binary_search(t, 98)} );
  TEST_FALSE( {type.binary_search(t, 21)} );
  TEST_FALSE( {type.binary_search(t, -1)} );
  TEST_FALSE( {type.binary_search(t, 100)} );

  TEST_EQUAL( {type.lower_bound(t, 20)}, 10 );
  TEST_EQUAL( {type.lower_bound(t, 21)}, 11 );
  TEST_EQUAL( {type.upper_bound(t, 20)}, 11 );
""")


x.setup(f"""
  int i;
  {t.definition};
  {type.create(t)};
""")
x.cleanup(f"""
  {type.destroy(t)};
""")

x.unit(f"{type.resize}(): resize up from empty", f"""
  {type.resize(t, 5)};
  TEST_FALSE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 5 );
  for(i = 0; i < 5; ++i) TEST_EQUAL( {type.get(t, "i")}, 0 );
""")

x.unit(f"{type.resize}(): resize up across the chunk boundaries", f"""
  {type.resize(t, 40)};
  TEST_EQUAL( {type.size(t)}, 40 );
  for(i = 0; i < 40; ++i) TEST_EQUAL( {type.get(t, "i")}, 0 );
""")

x.unit(f"{type.resize}(): resize into size zero is a no-op", f"""
  {type.resize(t, 0)};
  TEST_TRUE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 0 );
""")

x.unit(f"{type.resize}(): same size is a no-op", f"""
  {type.create_size(t, 40)};
  for(i = 0; i < 40; ++i) {type.set(t, "i", "i")};
  {type.resize(t, 40)};
  TEST_EQUAL( {type.size(t)}, 40 );
  for(i = 0; i < 40; ++i) TEST_EQUAL( {type.get(t, "i")}, i );
""")

x.unit(f"{type.resize}(): resize down releases the unused chunks", f"""
  {type.create_size(t, 40)};
  for(i = 0; i < 40; ++i) {type.set(t, "i", "i")};
  {type.resize(t, 20)};
  TEST_EQUAL( {type.size(t)}, 20 );
  for(i = 0; i < 20; ++i) TEST_EQUAL( {type.get(t, "i")}, i );
  /* the freed chunk is reused by the subsequent pushes */
  for(i = 20; i < 50; ++i) {type.push(t, "i")};
  TEST_EQUAL( {type.size(t)}, 50 );
  for(i = 0; i < 50; ++i) TEST_EQUAL( {type.get(t, "i")}, i );
""")

x.unit(f"{type.resize}(): resize to empty and back", f"""
  {type.create_size(t, 40)};
  {type.resize(t, 0)};
  TEST_TRUE( {type.empty(t)} );
  {type.resize(t, 10)};
  TEST_EQUAL( {type.size(t)}, 10 );
  for(i = 0; i < 10; ++i) TEST_EQUAL( {type.get(t, "i")}, 0 );
""")

x.unit(f"{type.resize}(): repeated up and down cycles", f"""
  {type.create_size(t, 40)};
  for(i = 0; i < 40; ++i) {type.set(t, "i", "i")};
  {type.resize(t, 70)};
  TEST_EQUAL( {type.size(t)}, 70 );
  for(i = 0; i < 40; ++i) TEST_EQUAL( {type.get(t, "i")}, i );
  for(i = 40; i < 70; ++i) TEST_EQUAL( {type.get(t, "i")}, 0 );
  {type.resize(t, 30)};
  TEST_EQUAL( {type.size(t)}, 30 );
  for(i = 0; i < 30; ++i) TEST_EQUAL( {type.get(t, "i")}, i );
  {type.resize(t, 45)};
  TEST_EQUAL( {type.size(t)}, 45 );
  for(i = 0; i < 30; ++i) TEST_EQUAL( {type.get(t, "i")}, i );
  for(i = 30; i < 45; ++i) TEST_EQUAL( {type.get(t, "i")}, 0 );
""")

x.setup(f"""
  {t.definition};
  {type.create(t)};
""")
x.cleanup(f"""
  {type.destroy(t)};
""")

x.unit(f"{type.put}()/{type.remove}(): container protocol addition and removal", f"""
  TEST_TRUE( {type.put(t, 10)} );
  TEST_TRUE( {type.put(t, 20)} );
  TEST_TRUE( {type.put(t, 30)} );
  TEST_EQUAL( {type.size(t)}, 3 );
  TEST_EQUAL( {type.get(t, 0)}, 10 );
  TEST_EQUAL( {type.get(t, 1)}, 20 );
  TEST_EQUAL( {type.get(t, 2)}, 30 );

  TEST_FALSE( {type.remove(t, 99)} );
  TEST_EQUAL( {type.size(t)}, 3 );

  /* remove middle element */
  TEST_TRUE( {type.remove(t, 20)} );
  TEST_EQUAL( {type.size(t)}, 2 );
  TEST_EQUAL( {type.get(t, 0)}, 10 );
  TEST_EQUAL( {type.get(t, 1)}, 30 );

  /* remove front element */
  TEST_TRUE( {type.remove(t, 10)} );
  TEST_EQUAL( {type.size(t)}, 1 );
  TEST_EQUAL( {type.get(t, 0)}, 30 );

  /* remove last remaining */
  TEST_TRUE( {type.remove(t, 30)} );
  TEST_TRUE( {type.empty(t)} );
  TEST_FALSE( {type.remove(t, 30)} );
""")

x.unit(f"{type.front}(), {type.back}(), {type.clear}(): element access and clear", f"""
  {type.push(t, 100)};
  {type.push(t, 200)};
  {type.push(t, 300)};
  TEST_EQUAL( {type.front(t)}, 100 );
  TEST_EQUAL( *{type.front_view(t)}, 100 );
  TEST_EQUAL( {type.back(t)}, 300 );
  TEST_EQUAL( *{type.back_view(t)}, 300 );

  {type.clear(t)};
  TEST_TRUE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 0 );
""")
