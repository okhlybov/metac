from metac.test import *
from metac.vector import Vector

type = Vector("int_inlined_vector", "int", inline_capacity=4)
x = Type(type)

t = type.variable("t")


x.setup(f"""
  {t.definition};
  {type.create(t)};
""")
x.cleanup(f"""
  {type.destroy(t)};
""")

x.unit(f"{type.empty}(): test empty inlined vector", f"""
  TEST_TRUE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 0 );
  TEST_EQUAL( {type.capacity(t)}, 4 );
  TEST_EQUAL( {type.data(t)}, t.storage.inline_elements );
""")

x.unit(f"{type.push}(): push within inline capacity", f"""
  {type.push(t, 100)};
  {type.push(t, 200)};
  {type.push(t, 300)};
  {type.push(t, 400)};
  TEST_EQUAL( {type.size(t)}, 4 );
  TEST_EQUAL( {type.capacity(t)}, 4 );
  TEST_EQUAL( {type.data(t)}, t.storage.inline_elements );
  TEST_EQUAL( {type.get(t, 0)}, 100 );
  TEST_EQUAL( {type.get(t, 1)}, 200 );
  TEST_EQUAL( {type.get(t, 2)}, 300 );
  TEST_EQUAL( {type.get(t, 3)}, 400 );
""")

x.unit(f"{type.push}(): push spills over to heap", f"""
  int i;
  for(i = 0; i < 4; ++i) {type.push(t, "i + 1")};
  TEST_EQUAL( {type.data(t)}, t.storage.inline_elements );

  /* 5th element exceeds inline capacity 4, causing heap allocation */
  {type.push(t, 5)};
  TEST_EQUAL( {type.size(t)}, 5 );
  TEST_TRUE( {type.capacity(t)} >= 8 );
  TEST_NOT_EQUAL( {type.data(t)}, t.storage.inline_elements );
  TEST_EQUAL( {type.data(t)}, t.storage.heap_elements );

  for(i = 0; i < 5; ++i) TEST_EQUAL( {type.get(t, "i")}, i + 1 );

  /* Push further onto heap */
  for(i = 5; i < 20; ++i) {type.push(t, "i + 1")};
  TEST_EQUAL( {type.size(t)}, 20 );
  for(i = 0; i < 20; ++i) TEST_EQUAL( {type.get(t, "i")}, i + 1 );
""")

x.unit(f"{type.pop}(): pop elements in LIFO order", f"""
  int i;
  for(i = 0; i < 6; ++i) {type.push(t, "i + 1")};
  TEST_EQUAL( {type.size(t)}, 6 );
  TEST_EQUAL( {type.pop(t)}, 6 );
  TEST_EQUAL( {type.pop(t)}, 5 );
  TEST_EQUAL( {type.pop(t)}, 4 );
  TEST_EQUAL( {type.size(t)}, 3 );
  TEST_EQUAL( {type.pop(t)}, 3 );
  TEST_EQUAL( {type.pop(t)}, 2 );
  TEST_EQUAL( {type.pop(t)}, 1 );
  TEST_TRUE( {type.empty(t)} );
""")

x.unit(f"{type.create_size}(): inline size vs heap size", f"""
  {type.destroy(t)};
  {type.create_size(t, 3)};
  TEST_EQUAL( {type.size(t)}, 3 );
  TEST_EQUAL( {type.capacity(t)}, 4 );
  TEST_EQUAL( {type.data(t)}, t.storage.inline_elements );

  {type.destroy(t)};
  {type.create_size(t, 8)};
  TEST_EQUAL( {type.size(t)}, 8 );
  TEST_EQUAL( {type.capacity(t)}, 8 );
  TEST_NOT_EQUAL( {type.data(t)}, t.storage.inline_elements );
""")

x.unit(f"{type.resize}(): resize within and exceeding inline capacity", f"""
  {type.resize(t, 2)};
  TEST_EQUAL( {type.size(t)}, 2 );
  TEST_EQUAL( {type.capacity(t)}, 4 );
  TEST_EQUAL( {type.data(t)}, t.storage.inline_elements );

  {type.set(t, 0, 11)};
  {type.set(t, 1, 22)};

  {type.resize(t, 6)};
  TEST_EQUAL( {type.size(t)}, 6 );
  TEST_TRUE( {type.capacity(t)} >= 6 );
  TEST_EQUAL( {type.get(t, 0)}, 11 );
  TEST_EQUAL( {type.get(t, 1)}, 22 );
  TEST_EQUAL( {type.get(t, 2)}, 0 );

  {type.resize(t, 1)};
  TEST_EQUAL( {type.size(t)}, 1 );
  TEST_EQUAL( {type.get(t, 0)}, 11 );
""")


other = type.variable("other")

x.setup(f"""
  int i;
  {t.definition};
  {other.definition};
  {type.create(t)};
  {type.create(other)};
""")
x.cleanup(f"""
  {type.destroy(t)};
  {type.destroy(other)};
""")

x.unit(f"{type.copy}(): copy inline vector", f"""
  for(i = 0; i < 3; ++i) {type.push(t, "i * 10")};
  {type.destroy(other)};
  {type.copy(other, t)};
  TEST_EQUAL( {type.size(other)}, 3 );
  TEST_EQUAL( {type.capacity(other)}, 4 );
  TEST_EQUAL( {type.data(other)}, other.storage.inline_elements );
  for(i = 0; i < 3; ++i) TEST_EQUAL( {type.get(other, "i")}, i * 10 );
""")

x.unit(f"{type.copy}(): copy heap spilled vector", f"""
  for(i = 0; i < 10; ++i) {type.push(t, "i * 10")};
  {type.destroy(other)};
  {type.copy(other, t)};
  TEST_EQUAL( {type.size(other)}, 10 );
  TEST_TRUE( {type.capacity(other)} >= 10 );
  TEST_NOT_EQUAL( {type.data(other)}, other.storage.inline_elements );
  for(i = 0; i < 10; ++i) TEST_EQUAL( {type.get(other, "i")}, i * 10 );
""")

x.unit(f"{type.move}(): move heap spilled vector steals pointer", f"""
  for(i = 0; i < 10; ++i) {type.push(t, "i * 10")};
  int *old_ptr = {type.data(t)};
  {type.destroy(other)};
  {type.move(other, t)};
  TEST_EQUAL( {type.size(other)}, 10 );
  TEST_EQUAL( {type.data(other)}, old_ptr );
  TEST_TRUE( {type.empty(t)} );
  TEST_EQUAL( {type.capacity(t)}, 4 );
""")

x.unit(f"{type.move}(): move inline vector", f"""
  for(i = 0; i < 3; ++i) {type.push(t, "i + 1")};
  {type.destroy(other)};
  {type.move(other, t)};
  TEST_EQUAL( {type.size(other)}, 3 );
  TEST_EQUAL( {type.capacity(other)}, 4 );
  TEST_EQUAL( {type.data(other)}, other.storage.inline_elements );
  for(i = 0; i < 3; ++i) TEST_EQUAL( {type.get(other, "i")}, i + 1 );
  TEST_TRUE( {type.empty(t)} );
""")

x.unit(f"{type.swap}(): swap inline with heap vector", f"""
  {type.push(t, 42)};
  for(i = 0; i < 8; ++i) {type.push(other, "i + 1")};
  int *other_heap = {type.data(other)};

  {type.swap(t, other)};

  TEST_EQUAL( {type.size(t)}, 8 );
  TEST_EQUAL( {type.data(t)}, other_heap );

  TEST_EQUAL( {type.size(other)}, 1 );
  TEST_EQUAL( {type.data(other)}, other.storage.inline_elements );
  TEST_EQUAL( {type.get(other, 0)}, 42 );
""")


x.setup(f"""
  int i;
  {t.definition};
  {type.create(t)};
""")
x.cleanup(f"""
  {type.destroy(t)};
""")

x.unit(f"{type.sort}(): sort inlined vector", f"""
  {type.push(t, 40)};
  {type.push(t, 10)};
  {type.push(t, 30)};
  {type.push(t, 20)};
  TEST_FALSE( {type.sorted(t)} );
  {type.sort(t)};
  TEST_TRUE( {type.sorted(t)} );
  TEST_EQUAL( {type.get(t, 0)}, 10 );
  TEST_EQUAL( {type.get(t, 1)}, 20 );
  TEST_EQUAL( {type.get(t, 2)}, 30 );
  TEST_EQUAL( {type.get(t, 3)}, 40 );
""")

x.unit(f"{type.reverse}(): reverse inlined and heap vector", f"""
  for(i = 0; i < 4; ++i) {type.push(t, "i")};
  {type.reverse(t)};
  for(i = 0; i < 4; ++i) TEST_EQUAL( {type.get(t, "i")}, 3 - i );

  {type.destroy(t)};
  {type.create(t)};
  for(i = 0; i < 8; ++i) {type.push(t, "i")};
  {type.reverse(t)};
  for(i = 0; i < 8; ++i) TEST_EQUAL( {type.get(t, "i")}, 7 - i );
""")

x.unit(f"{type.binary_search}(): binary search inlined vector", f"""
  for(i = 0; i < 4; ++i) {type.push(t, "i * 10")};
  TEST_TRUE( {type.binary_search(t, 20)} );
  TEST_FALSE( {type.binary_search(t, 25)} );
  TEST_EQUAL( {type.lower_bound(t, 20)}, 2 );
  TEST_EQUAL( {type.upper_bound(t, 20)}, 3 );
""")

r = type.range.variable("r")

x.unit(f"{type.range.new}(): traverse inlined vector via range", f"""
  {r.definition};
  int sum = 0;
  for(i = 1; i <= 4; ++i) {type.push(t, "i")};
  for(r = {type.range.new(t)}; !{type.range.empty(r)}; {type.range.move_front(r)}) {{
    sum += {type.range.front(r)};
  }}
  TEST_EQUAL( sum, 10 );
""")

x.unit(f"{type.range.new}(): traverse inlined vector crossing inline capacity boundary", f"""
  {r.definition};
  int sum = 0, expected = 0;
  for(i = 1; i <= 10; ++i) {{
    {type.push(t, "i")};
    expected += i;
  }}
  TEST_EQUAL( {type.size(t)}, 10 );
  TEST_NOT_EQUAL( {type.data(t)}, t.storage.inline_elements );
  TEST_EQUAL( {type.data(t)}, t.storage.heap_elements );

  /* Forward range traversal */
  for(r = {type.range.new(t)}; !{type.range.empty(r)}; {type.range.move_front(r)}) {{
    sum += {type.range.front(r)};
  }}
  TEST_EQUAL( sum, expected );

  /* Backward range traversal */
  r = {type.range.new(t)};
  TEST_EQUAL( {type.range.size(r)}, 10 );
  for(i = 10; i >= 1; --i) {{
    TEST_FALSE( {type.range.empty(r)} );
    TEST_EQUAL( {type.range.back(r)}, i );
    {type.range.move_back(r)};
  }}
  TEST_TRUE( {type.range.empty(r)} );

  /* Direct indexing via range */
  r = {type.range.new(t)};
  for(i = 0; i < 10; ++i) {{
    TEST_EQUAL( {type.range.get(r, "i")}, i + 1 );
    TEST_EQUAL( *{type.range.view(r, "i")}, i + 1 );
  }}
""")

x.unit(f"{type.range.new}(): range iteration across storage transition on same instance", f"""
  {r.definition};
  int sum = 0;

  /* Phase 1: Inlined buffer mode (3 elements <= 4) */
  {type.push(t, 10)};
  {type.push(t, 20)};
  {type.push(t, 30)};
  TEST_EQUAL( {type.size(t)}, 3 );
  TEST_EQUAL( {type.capacity(t)}, 4 );
  TEST_EQUAL( {type.data(t)}, t.storage.inline_elements );

  sum = 0;
  for(r = {type.range.new(t)}; !{type.range.empty(r)}; {type.range.move_front(r)}) {{
    sum += {type.range.front(r)};
  }}
  TEST_EQUAL( sum, 60 );

  r = {type.range.new(t)};
  TEST_EQUAL( {type.range.size(r)}, 3 );
  TEST_EQUAL( {type.range.front(r)}, 10 );
  TEST_EQUAL( {type.range.back(r)}, 30 );
  TEST_EQUAL( {type.range.get(r, 1)}, 20 );

  /* Phase 2: Spill the very same instance into dynamic buffer (push to 7 elements > 4) */
  {type.push(t, 40)};
  {type.push(t, 50)};
  {type.push(t, 60)};
  {type.push(t, 70)};
  TEST_EQUAL( {type.size(t)}, 7 );
  TEST_TRUE( {type.capacity(t)} >= 7 );
  TEST_NOT_EQUAL( {type.data(t)}, t.storage.inline_elements );
  TEST_EQUAL( {type.data(t)}, t.storage.heap_elements );

  sum = 0;
  for(r = {type.range.new(t)}; !{type.range.empty(r)}; {type.range.move_front(r)}) {{
    sum += {type.range.front(r)};
  }}
  TEST_EQUAL( sum, 280 );

  r = {type.range.new(t)};
  TEST_EQUAL( {type.range.size(r)}, 7 );
  TEST_EQUAL( {type.range.front(r)}, 10 );
  TEST_EQUAL( {type.range.back(r)}, 70 );
  for(i = 0; i < 7; ++i) {{
    TEST_EQUAL( {type.range.get(r, "i")}, (i + 1) * 10 );
    TEST_EQUAL( *{type.range.view(r, "i")}, (i + 1) * 10 );
  }}
""")

x.unit(f"{type.compact}(): revert heap spilled vector back to inlined buffer", f"""
  for(i = 0; i < 8; ++i) {type.push(t, "(i + 1) * 10")};
  TEST_EQUAL( {type.size(t)}, 8 );
  TEST_TRUE( {type.capacity(t)} >= 8 );
  TEST_EQUAL( {type.data(t)}, t.storage.heap_elements );

  /* Pop 6 elements so size becomes 2 (<= inline capacity 4) */
  for(i = 0; i < 6; ++i) {type.pop(t)};
  TEST_EQUAL( {type.size(t)}, 2 );
  TEST_EQUAL( {type.data(t)}, t.storage.heap_elements );

  /* compact should revert to inline buffer */
  {type.compact(t)};
  TEST_EQUAL( {type.size(t)}, 2 );
  TEST_EQUAL( {type.capacity(t)}, 4 );
  TEST_EQUAL( {type.data(t)}, t.storage.inline_elements );
  TEST_EQUAL( {type.get(t, 0)}, 10 );
  TEST_EQUAL( {type.get(t, 1)}, 20 );

  /* Further operations work on the reverted inline buffer */
  {type.push(t, 30)};
  {type.push(t, 40)};
  TEST_EQUAL( {type.size(t)}, 4 );
  TEST_EQUAL( {type.capacity(t)}, 4 );
  TEST_EQUAL( {type.data(t)}, t.storage.inline_elements );
""")

x.unit(f"{type.compact}(): shrink heap vector without reverting when size > inline capacity", f"""
  for(i = 0; i < 16; ++i) {type.push(t, "i + 1")};
  TEST_EQUAL( {type.size(t)}, 16 );
  TEST_TRUE( {type.capacity(t)} >= 16 );

  /* Pop down to 6 elements (which is still > inline capacity 4) */
  for(i = 0; i < 10; ++i) {type.pop(t)};
  TEST_EQUAL( {type.size(t)}, 6 );

  /* compact should reduce heap capacity to exact size 6 */
  {type.compact(t)};
  TEST_EQUAL( {type.size(t)}, 6 );
  TEST_EQUAL( {type.capacity(t)}, 6 );
  TEST_EQUAL( {type.data(t)}, t.storage.heap_elements );
  for(i = 0; i < 6; ++i) TEST_EQUAL( {type.get(t, "i")}, i + 1 );
""")

x.unit(f"{type.compact}(): shrink empty spilled vector to inline buffer", f"""
  for(i = 0; i < 8; ++i) {type.push(t, "i + 1")};
  TEST_EQUAL( {type.data(t)}, t.storage.heap_elements );

  for(i = 0; i < 8; ++i) {type.pop(t)};
  TEST_TRUE( {type.empty(t)} );
  TEST_EQUAL( {type.data(t)}, t.storage.heap_elements );

  {type.compact(t)};
  TEST_TRUE( {type.empty(t)} );
  TEST_EQUAL( {type.capacity(t)}, 4 );
  TEST_EQUAL( {type.data(t)}, t.storage.inline_elements );
""")
