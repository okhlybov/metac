from metac.test import *
from metac.circular_buffer import Static, Dynamic
from metac.test.cstring import cstring, s

#
# 1. Tests for Static circular buffer with cstring
#
x = Type(type := Static("cstring_scb", cstring, 3))

t = type.variable("t")
t2 = type.variable("t2")
r = type.range.variable("r")

x.setup(f"""
  {t.definition};
  {type.create(t)};
""")
x.cleanup(f"""
  {type.destroy(t)};
""")

x.unit(f"{type.push}(): push strings within capacity and overwrite when full", f"""
  char* v;
  {type.push(t, s("first"))};
  {type.push(t, s("second"))};
  {type.push(t, s("third"))};
  TEST_TRUE( {type.full(t)} );
  TEST_EQUAL( {type.size(t)}, 3 );
  TEST_EQUAL_CHARS( {type.front_view(t)}, {s("first")} );
  TEST_EQUAL_CHARS( {type.back_view(t)}, {s("third")} );

  /* 4th push overwrites oldest ("first") */
  {type.push(t, s("fourth"))};
  TEST_TRUE( {type.full(t)} );
  TEST_EQUAL( {type.size(t)}, 3 );
  TEST_EQUAL_CHARS( {type.front_view(t)}, {s("second")} );
  TEST_EQUAL_CHARS( {type.back_view(t)}, {s("fourth")} );

  /* pop front */
  v = {type.pop(t)};
  TEST_EQUAL_CHARS( v, {s("second")} );
  {cstring.destroy("v")};
  TEST_EQUAL( {type.size(t)}, 2 );
  TEST_EQUAL_CHARS( {type.front_view(t)}, {s("third")} );
""")

x.unit(f"{type.push_front}(): push_front strings and overwrite when full", f"""
  char* v;
  {type.push_front(t, s("c"))};
  {type.push_front(t, s("b"))};
  {type.push_front(t, s("a"))};
  TEST_TRUE( {type.full(t)} );
  TEST_EQUAL_CHARS( {type.front_view(t)}, {s("a")} );
  TEST_EQUAL_CHARS( {type.back_view(t)}, {s("c")} );

  /* push_front on full overwrites back ("c") */
  {type.push_front(t, s("z"))};
  TEST_TRUE( {type.full(t)} );
  TEST_EQUAL_CHARS( {type.front_view(t)}, {s("z")} );
  TEST_EQUAL_CHARS( {type.back_view(t)}, {s("b")} );

  v = {type.pop_back(t)};
  TEST_EQUAL_CHARS( v, {s("b")} );
  {cstring.destroy("v")};
  TEST_EQUAL( {type.size(t)}, 2 );
""")

x.unit(f"{type.clear}(): clear strings and reuse", f"""
  {type.push(t, s("hello"))};
  {type.push(t, s("world"))};
  TEST_EQUAL( {type.size(t)}, 2 );
  {type.clear(t)};
  TEST_TRUE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 0 );

  {type.push(t, s("reused"))};
  TEST_EQUAL( {type.size(t)}, 1 );
  TEST_EQUAL_CHARS( {type.front_view(t)}, {s("reused")} );
""")

x.unit(f"{type.copy}(), {type.equal}(): copy and equality with cstring", f"""
  {t2.definition};
  {type.create(t2)};
  {type.push(t, s("one"))};
  {type.push(t, s("two"))};
  {type.copy(t2, t)};
  TEST_TRUE( {type.equal(t, t2)} );
  TEST_EQUAL_CHARS( {type.front_view(t2)}, {s("one")} );
  TEST_EQUAL_CHARS( {type.back_view(t2)}, {s("two")} );
  {type.destroy(t2)};
""")


#
# 2. Tests for Dynamic circular buffer with cstring
#
y = Type(dtype := Dynamic("cstring_dcb", cstring))

dt = dtype.variable("dt")
dt2 = dtype.variable("dt2")

y.setup(f"""
  {dt.definition};
  {dtype.create(dt, 3)};
""")
y.cleanup(f"""
  {dtype.destroy(dt)};
""")

y.unit(f"{dtype.push}(): dynamic buffer push and overwrite with cstring", f"""
  char* v;
  {dtype.push(dt, s("alpha"))};
  {dtype.push(dt, s("beta"))};
  {dtype.push(dt, s("gamma"))};
  TEST_TRUE( {dtype.full(dt)} );

  /* overwrite oldest ("alpha") */
  {dtype.push(dt, s("delta"))};
  TEST_TRUE( {dtype.full(dt)} );
  TEST_EQUAL( {dtype.size(dt)}, 3 );
  TEST_EQUAL_CHARS( {dtype.front_view(dt)}, {s("beta")} );
  TEST_EQUAL_CHARS( {dtype.back_view(dt)}, {s("delta")} );

  v = {dtype.pop(dt)};
  TEST_EQUAL_CHARS( v, {s("beta")} );
  {cstring.destroy("v")};
""")

y.unit(f"{dtype.set_capacity}(): dynamic buffer resizing with cstring", f"""
  {dtype.push(dt, s("A"))};
  {dtype.push(dt, s("B"))};
  {dtype.push(dt, s("C"))};

  /* Expand to 5 */
  {dtype.set_capacity(dt, 5)};
  TEST_EQUAL( {dtype.capacity(dt)}, 5 );
  TEST_EQUAL( {dtype.size(dt)}, 3 );
  TEST_EQUAL_CHARS( {dtype.front_view(dt)}, {s("A")} );
  TEST_EQUAL_CHARS( {dtype.back_view(dt)}, {s("C")} );

  {dtype.push(dt, s("D"))};
  {dtype.push(dt, s("E"))};
  TEST_TRUE( {dtype.full(dt)} );
  TEST_EQUAL( {dtype.size(dt)}, 5 );

  /* Shrink to 2: oldest elements (A, B, C) are discarded, D and E kept */
  {dtype.set_capacity(dt, 2)};
  TEST_EQUAL( {dtype.capacity(dt)}, 2 );
  TEST_EQUAL( {dtype.size(dt)}, 2 );
  TEST_TRUE( {dtype.full(dt)} );
  TEST_EQUAL_CHARS( {dtype.front_view(dt)}, {s("D")} );
  TEST_EQUAL_CHARS( {dtype.back_view(dt)}, {s("E")} );
""")

y.unit(f"{dtype.copy}(), {dtype.move}(): dynamic buffer copy and move with cstring", f"""
  {dt2.definition};
  {dtype.push(dt, s("first"))};
  {dtype.push(dt, s("second"))};

  {dtype.copy(dt2, dt)};
  TEST_TRUE( {dtype.equal(dt, dt2)} );
  TEST_EQUAL_CHARS( {dtype.front_view(dt2)}, {s("first")} );
  TEST_EQUAL_CHARS( {dtype.back_view(dt2)}, {s("second")} );
  {dtype.destroy(dt2)};

  {dtype.move(dt2, dt)};
  TEST_TRUE( {dtype.empty(dt)} );
  TEST_EQUAL( {dtype.size(dt2)}, 2 );
  TEST_EQUAL_CHARS( {dtype.front_view(dt2)}, {s("first")} );
  TEST_EQUAL_CHARS( {dtype.back_view(dt2)}, {s("second")} );
  {dtype.destroy(dt2)};
""")
