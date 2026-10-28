from metac.test import *
from metac.vector import Vector

x = Type(type := Vector("int_vector", "int"))

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
  {type.create(t)};
""")
x.cleanup(f"""
  {type.destroy(t)};
""")

x.unit(f"{type.sort}(): sort empty vector", f"""
  {type.sort(t)};
  TEST_TRUE( {type.sorted(t)} );
  TEST_EQUAL( {type.size(t)}, 0 );
""")


x.setup(f"""
  int i;
  {t.definition};
  {type.create_size(t, 8)};
""")
x.cleanup(f"""
  {type.destroy(t)};
""")

x.unit(f"{type.sort}(): sort descending vector", f"""
  for(i = 0; i < 8; ++i) {type.set(t, "i", "8 - i")};
  TEST_FALSE( {type.sorted(t)} );
  {type.sort(t)};
  TEST_TRUE( {type.sorted(t)} );
  for(i = 0; i < 8; ++i) TEST_EQUAL( {type.get(t, "i")}, i + 1 );
""")

x.unit(f"{type.sort}(): sort vector with duplicates", f"""
  int expected[] = {{1, 1, 2, 2, 3, 3, 4, 4}};
  {type.set(t, 0, 3)}; {type.set(t, 1, 1)}; {type.set(t, 2, 4)}; {type.set(t, 3, 1)};
  {type.set(t, 4, 3)}; {type.set(t, 5, 2)}; {type.set(t, 6, 4)}; {type.set(t, 7, 2)};
  {type.sort(t)};
  TEST_TRUE( {type.sorted(t)} );
  for(i = 0; i < 8; ++i) TEST_EQUAL( {type.get(t, "i")}, expected[i] );
""")

x.unit(f"{type.sort}(): sort all equal elements", f"""
  for(i = 0; i < 8; ++i) {type.set(t, "i", 7)};
  {type.sort(t)};
  TEST_TRUE( {type.sorted(t)} );
  TEST_EQUAL( {type.get(t, 3)}, 7 );
""")

x.unit(f"{type.sort}(): sort already sorted vector", f"""
  for(i = 0; i < 8; ++i) {type.set(t, "i", "i")};
  {type.sort(t)};
  TEST_TRUE( {type.sorted(t)} );
  for(i = 0; i < 8; ++i) TEST_EQUAL( {type.get(t, "i")}, i );
""")


x.setup(f"""
  int i;
  long long sum;
  {t.definition};
  {type.create_size(t, 64)};
""")
x.cleanup(f"""
  {type.destroy(t)};
""")

x.unit(f"{type.sort}(): sort permutation of 64 elements", f"""
  for(i = 0; i < 64; ++i) {type.set(t, "i", "(i*37 + 11)%64")};
  sum = 0;
  for(i = 0; i < 64; ++i) sum += {type.get(t, "i")};
  TEST_EQUAL( sum, 2016 );
  {type.sort(t)};
  TEST_TRUE( {type.sorted(t)} );
  TEST_EQUAL( {type.get(t, 0)}, 0 );
  TEST_EQUAL( {type.get(t, 63)}, 63 );
  sum = 0;
  for(i = 0; i < 64; ++i) sum += {type.get(t, "i")};
  TEST_EQUAL( sum, 2016 );
""")

x.unit(f"{type.sort}(): sort >= 16 equal elements exercising quicksort", f"""
  for(i = 0; i < 64; ++i) {type.set(t, "i", 42)};
  {type.sort(t)};
  TEST_TRUE( {type.sorted(t)} );
  TEST_EQUAL( {type.get(t, 0)}, 42 );
  TEST_EQUAL( {type.get(t, 63)}, 42 );
""")


x.setup(f"""
  int i;
  {t.definition};
  {type.create_size(t, 8)};
""")
x.cleanup(f"""
  {type.destroy(t)};
""")

x.unit(f"{type.reverse}(): reverse descending vector into ascending", f"""
  for(i = 0; i < 8; ++i) {type.set(t, "i", "8 - i")};
  {type.reverse(t)};
  TEST_TRUE( {type.sorted(t)} );
  for(i = 0; i < 8; ++i) TEST_EQUAL( {type.get(t, "i")}, i + 1 );
""")

x.unit(f"{type.reverse}(): reverse twice restores the original", f"""
  for(i = 0; i < 8; ++i) {type.set(t, "i", "i*3 % 8")};
  {type.reverse(t)};
  {type.reverse(t)};
  for(i = 0; i < 8; ++i) TEST_EQUAL( {type.get(t, "i")}, i*3 % 8 );
""")

x.unit(f"{type.reverse}(): reverse empty and single element vectors", f"""
  {type.destroy(t)};
  {type.create(t)};
  {type.reverse(t)};
  TEST_TRUE( {type.empty(t)} );
  {type.create_size(t, 1)};
  {type.set(t, 0, 5)};
  {type.reverse(t)};
  TEST_EQUAL( {type.get(t, 0)}, 5 );
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
  {type.resize(t, 8)};
  TEST_FALSE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 8 );
  for(i = 0; i < 8; ++i) TEST_EQUAL( {type.get(t, "i")}, 0 );
""")

x.unit(f"{type.resize}(): resize up into size zero is a no-op", f"""
  {type.resize(t, 0)};
  TEST_TRUE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 0 );
""")

x.unit(f"{type.resize}(): resize down preserves the head", f"""
  {type.create_size(t, 8)};
  for(i = 0; i < 8; ++i) {type.set(t, "i", "i")};
  {type.resize(t, 3)};
  TEST_EQUAL( {type.size(t)}, 3 );
  for(i = 0; i < 3; ++i) TEST_EQUAL( {type.get(t, "i")}, i );
""")

x.unit(f"{type.resize}(): same size is a no-op", f"""
  {type.create_size(t, 4)};
  {type.set(t, 0, 1)}; {type.set(t, 1, 2)}; {type.set(t, 2, 3)}; {type.set(t, 3, 4)};
  {type.resize(t, 4)};
  TEST_EQUAL( {type.size(t)}, 4 );
  TEST_EQUAL( {type.get(t, 0)}, 1 );
  TEST_EQUAL( {type.get(t, 3)}, 4 );
""")

x.unit(f"{type.resize}(): resize up re-default-initializes the tail", f"""
  {type.create_size(t, 4)};
  for(i = 0; i < 4; ++i) {type.set(t, "i", "i + 1")};
  {type.resize(t, 6)};
  TEST_EQUAL( {type.size(t)}, 6 );
  TEST_EQUAL( {type.get(t, 3)}, 4 );
  for(i = 4; i < 6; ++i) TEST_EQUAL( {type.get(t, "i")}, 0 );
""")

x.unit(f"{type.resize}(): resize to empty and back", f"""
  {type.create_size(t, 4)};
  {type.resize(t, 0)};
  TEST_TRUE( {type.empty(t)} );
  {type.resize(t, 2)};
  TEST_EQUAL( {type.size(t)}, 2 );
  for(i = 0; i < 2; ++i) TEST_EQUAL( {type.get(t, "i")}, 0 );
""")

x.unit(f"{type.resize}(): repeated up and down cycles", f"""
  {type.create_size(t, 4)};
  for(i = 0; i < 4; ++i) {type.set(t, "i", "i")};
  {type.resize(t, 10)};
  TEST_EQUAL( {type.size(t)}, 10 );
  for(i = 0; i < 4; ++i) TEST_EQUAL( {type.get(t, "i")}, i );
  {type.resize(t, 2)};
  TEST_EQUAL( {type.size(t)}, 2 );
  TEST_EQUAL( {type.get(t, 1)}, 1 );
  {type.resize(t, 5)};
  TEST_EQUAL( {type.size(t)}, 5 );
  TEST_EQUAL( {type.get(t, 1)}, 1 );
  for(i = 2; i < 5; ++i) TEST_EQUAL( {type.get(t, "i")}, 0 );
""")

x.setup(f"""
  int i;
  {t.definition};
  {type.create(t)};
""")
x.cleanup(f"""
  {type.destroy(t)};
""")

x.unit(f"{type.push}(): push into empty vector grows geometrically", f"""
  TEST_EQUAL( {type.size(t)}, 0 );
  TEST_EQUAL( {type.capacity(t)}, 0 );
  {type.push(t, 10)};
  TEST_EQUAL( {type.size(t)}, 1 );
  TEST_TRUE( {type.capacity(t)} >= 1 );
  TEST_EQUAL( {type.get(t, 0)}, 10 );

  for(i = 1; i < 20; ++i) {type.push(t, "(i + 1) * 10")};
  TEST_EQUAL( {type.size(t)}, 20 );
  TEST_TRUE( {type.capacity(t)} >= 20 );
  for(i = 0; i < 20; ++i) TEST_EQUAL( {type.get(t, "i")}, (i + 1) * 10 );
""")

x.unit(f"{type.pop}(): pop elements in LIFO order", f"""
  for(i = 0; i < 5; ++i) {type.push(t, "i + 1")};
  TEST_EQUAL( {type.size(t)}, 5 );
  TEST_EQUAL( {type.pop(t)}, 5 );
  TEST_EQUAL( {type.pop(t)}, 4 );
  TEST_EQUAL( {type.size(t)}, 3 );
  TEST_EQUAL( {type.get(t, 2)}, 3 );
  TEST_EQUAL( {type.pop(t)}, 3 );
  TEST_EQUAL( {type.pop(t)}, 2 );
  TEST_EQUAL( {type.pop(t)}, 1 );
  TEST_TRUE( {type.empty(t)} );
""")

x.unit(f"{type.data}(): access contiguous buffer", f"""
  for(i = 0; i < 4; ++i) {type.push(t, "i * 2")};
  int *data = {type.data(t)};
  TEST_NOT_NULL( data );
  for(i = 0; i < 4; ++i) TEST_EQUAL( data[i], i * 2 );
""")

x.unit(f"{type.compact}(): compact capacity to size", f"""
  for(i = 0; i < 16; ++i) {type.push(t, "i + 1")};
  TEST_EQUAL( {type.size(t)}, 16 );
  TEST_TRUE( {type.capacity(t)} >= 16 );

  for(i = 0; i < 11; ++i) {type.pop(t)};
  TEST_EQUAL( {type.size(t)}, 5 );
  TEST_TRUE( {type.capacity(t)} >= 16 );

  {type.compact(t)};
  TEST_EQUAL( {type.size(t)}, 5 );
  TEST_EQUAL( {type.capacity(t)}, 5 );
  for(i = 0; i < 5; ++i) TEST_EQUAL( {type.get(t, "i")}, i + 1 );

  for(i = 0; i < 5; ++i) {type.pop(t)};
  TEST_TRUE( {type.empty(t)} );
  {type.compact(t)};
  TEST_EQUAL( {type.capacity(t)}, 0 );
  TEST_NULL( {type.data(t)} );
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
