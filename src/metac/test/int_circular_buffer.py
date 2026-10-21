from metac.test import *
from metac.circular_buffer import Static, Dynamic

#
# 1. Tests for Static circular buffer
#
x = Type(type := Static("int_scb", "int", 4))

t = type.variable("t")
t2 = type.variable("t2")
r = type.range.variable("r")

x.setup(f"""
  {t.definition};
  {type.create(t)};
""")
x.cleanup(f"""
  {type.destroy(t) if type.destructible else str()};
""")

x.unit(f"{type.empty}(): test initial state", f"""
  TEST_TRUE( {type.empty(t)} );
  TEST_FALSE( {type.full(t)} );
  TEST_EQUAL( {type.size(t)}, 0 );
  TEST_EQUAL( {type.capacity(t)}, 4 );
""")

x.unit(f"{type.push}(): push elements within capacity", f"""
  {type.push(t, 10)};
  TEST_FALSE( {type.empty(t)} );
  TEST_FALSE( {type.full(t)} );
  TEST_EQUAL( {type.size(t)}, 1 );
  TEST_EQUAL( {type.front(t)}, 10 );
  TEST_EQUAL( {type.back(t)}, 10 );
  TEST_EQUAL( *{type.front_view(t)}, 10 );
  TEST_EQUAL( *{type.back_view(t)}, 10 );

  {type.push(t, 20)};
  {type.push(t, 30)};
  {type.push(t, 40)};
  TEST_TRUE( {type.full(t)} );
  TEST_EQUAL( {type.size(t)}, 4 );
  TEST_EQUAL( {type.get(t, 0)}, 10 );
  TEST_EQUAL( {type.get(t, 1)}, 20 );
  TEST_EQUAL( {type.get(t, 2)}, 30 );
  TEST_EQUAL( {type.get(t, 3)}, 40 );
  TEST_EQUAL( {type.front(t)}, 10 );
  TEST_EQUAL( {type.back(t)}, 40 );
""")

x.unit(f"{type.push}(): overwrite oldest element when full", f"""
  {type.push(t, 1)};
  {type.push(t, 2)};
  {type.push(t, 3)};
  {type.push(t, 4)};
  TEST_TRUE( {type.full(t)} );

  /* 5th element overwrites oldest (1) */
  {type.push(t, 5)};
  TEST_TRUE( {type.full(t)} );
  TEST_EQUAL( {type.size(t)}, 4 );
  TEST_EQUAL( {type.front(t)}, 2 );
  TEST_EQUAL( {type.back(t)}, 5 );
  TEST_EQUAL( {type.get(t, 0)}, 2 );
  TEST_EQUAL( {type.get(t, 1)}, 3 );
  TEST_EQUAL( {type.get(t, 2)}, 4 );
  TEST_EQUAL( {type.get(t, 3)}, 5 );

  /* 6th element overwrites oldest (2) */
  {type.push_back(t, 6)};
  TEST_TRUE( {type.full(t)} );
  TEST_EQUAL( {type.size(t)}, 4 );
  TEST_EQUAL( {type.front(t)}, 3 );
  TEST_EQUAL( {type.back(t)}, 6 );
  TEST_EQUAL( {type.get(t, 0)}, 3 );
  TEST_EQUAL( {type.get(t, 1)}, 4 );
  TEST_EQUAL( {type.get(t, 2)}, 5 );
  TEST_EQUAL( {type.get(t, 3)}, 6 );
""")

x.unit(f"{type.push_front}(): push_front within capacity and overwrite when full", f"""
  {type.push_front(t, 10)};
  {type.push_front(t, 20)};
  TEST_EQUAL( {type.size(t)}, 2 );
  TEST_EQUAL( {type.front(t)}, 20 );
  TEST_EQUAL( {type.back(t)}, 10 );

  {type.push_front(t, 30)};
  {type.push_front(t, 40)};
  TEST_TRUE( {type.full(t)} );
  TEST_EQUAL( {type.get(t, 0)}, 40 );
  TEST_EQUAL( {type.get(t, 1)}, 30 );
  TEST_EQUAL( {type.get(t, 2)}, 20 );
  TEST_EQUAL( {type.get(t, 3)}, 10 );

  /* push_front when full overwrites the newest element at the back (10) */
  {type.push_front(t, 50)};
  TEST_TRUE( {type.full(t)} );
  TEST_EQUAL( {type.size(t)}, 4 );
  TEST_EQUAL( {type.front(t)}, 50 );
  TEST_EQUAL( {type.back(t)}, 20 );
  TEST_EQUAL( {type.get(t, 0)}, 50 );
  TEST_EQUAL( {type.get(t, 1)}, 40 );
  TEST_EQUAL( {type.get(t, 2)}, 30 );
  TEST_EQUAL( {type.get(t, 3)}, 20 );
""")

x.unit(f"{type.pop}(), {type.pop_back}(): pop and pop_back down to empty", f"""
  {type.push(t, 100)};
  {type.push(t, 200)};
  {type.push(t, 300)};
  {type.push(t, 400)};

  /* pop removes front */
  TEST_EQUAL( {type.pop(t)}, 100 );
  TEST_EQUAL( {type.size(t)}, 3 );
  TEST_EQUAL( {type.front(t)}, 200 );

  /* pop_back removes back */
  TEST_EQUAL( {type.pop_back(t)}, 400 );
  TEST_EQUAL( {type.size(t)}, 2 );
  TEST_EQUAL( {type.back(t)}, 300 );

  /* pop_front removes front */
  TEST_EQUAL( {type.pop_front(t)}, 200 );
  TEST_EQUAL( {type.size(t)}, 1 );
  TEST_EQUAL( {type.front(t)}, 300 );

  /* pop last element */
  TEST_EQUAL( {type.pop(t)}, 300 );
  TEST_TRUE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 0 );
""")

x.unit(f"{type.set}(), {type.indexed}(): set and indexed access", f"""
  {type.push(t, 10)};
  {type.push(t, 20)};
  {type.push(t, 30)};
  TEST_TRUE( {type.indexed(t, 0)} );
  TEST_TRUE( {type.indexed(t, 1)} );
  TEST_TRUE( {type.indexed(t, 2)} );
  TEST_FALSE( {type.indexed(t, 3)} );

  {type.set(t, 1, 999)};
  TEST_EQUAL( {type.get(t, 1)}, 999 );
  TEST_EQUAL( *{type.view(t, 1)}, 999 );
""")

x.unit(f"{type.clear}(): clear elements", f"""
  {type.push(t, 1)};
  {type.push(t, 2)};
  {type.push(t, 3)};
  TEST_EQUAL( {type.size(t)}, 3 );
  {type.clear(t)};
  TEST_TRUE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 0 );

  /* Push again after clear */
  {type.push(t, 42)};
  TEST_EQUAL( {type.size(t)}, 1 );
  TEST_EQUAL( {type.front(t)}, 42 );
""")

x.unit(f"{type.range}(): iterate range forward, backward, and direct index", f"""
  int sum = 0;
  {r.definition};
  {type.push(t, 10)};
  {type.push(t, 20)};
  {type.push(t, 30)};
  {type.push(t, 40)};
  /* overwrite to make head non-zero */
  {type.push(t, 50)};

  /* Elements are: 20, 30, 40, 50 */
  for({r} = {type.range.new(t)}; !{type.range.empty(r)}; {type.range.move_front(r)}) {{
    sum += {type.range.front(r)};
  }}
  TEST_EQUAL( sum, 140 );

  /* Direct access in range */
  {r} = {type.range.new(t)};
  TEST_EQUAL( {type.range.size(r)}, 4 );
  TEST_EQUAL( {type.range.get(r, 0)}, 20 );
  TEST_EQUAL( {type.range.get(r, 1)}, 30 );
  TEST_EQUAL( {type.range.get(r, 2)}, 40 );
  TEST_EQUAL( {type.range.get(r, 3)}, 50 );
  TEST_EQUAL( *{type.range.view(r, 3)}, 50 );

  /* Move back */
  TEST_EQUAL( {type.range.back(r)}, 50 );
  {type.range.move_back(r)};
  TEST_EQUAL( {type.range.back(r)}, 40 );
  TEST_EQUAL( {type.range.size(r)}, 3 );
""")

x.unit(f"{type.copy}(), {type.equal}(), {type.hash}(): copy, equality, and hash", f"""
  {t2.definition};
  {type.create(t2)};
  {type.push(t, 11)};
  {type.push(t, 22)};
  {type.push(t, 33)};
  {type.copy(t2, t)};

  TEST_TRUE( {type.equal(t, t2)} );
  TEST_EQUAL( {type.hash(t)}, {type.hash(t2)} );
  TEST_EQUAL( {type.size(t2)}, 3 );
  TEST_EQUAL( {type.get(t2, 0)}, 11 );
  TEST_EQUAL( {type.get(t2, 1)}, 22 );
  TEST_EQUAL( {type.get(t2, 2)}, 33 );

  {type.destroy(t2) if type.destructible else str()};
""")

x.unit(f"{type.move}(), {type.swap}(): move and swap", f"""
  {t2.definition};
  {type.create(t2)};
  {type.push(t, 100)};
  {type.push(t, 200)};

  /* Move t into t2 */
  {type.move(t2, t)};
  TEST_EQUAL( {type.size(t2)}, 2 );
  TEST_EQUAL( {type.get(t2, 0)}, 100 );
  TEST_EQUAL( {type.get(t2, 1)}, 200 );
  TEST_TRUE( {type.empty(t)} );

  /* Push into t, then swap */
  {type.push(t, 999)};
  {type.swap(t, t2)};
  TEST_EQUAL( {type.size(t)}, 2 );
  TEST_EQUAL( {type.front(t)}, 100 );
  TEST_EQUAL( {type.size(t2)}, 1 );
  TEST_EQUAL( {type.front(t2)}, 999 );

  {type.destroy(t2) if type.destructible else str()};
""")

x.unit(f"{type.contains}(): test contains for present and absent elements", f"""
  {type.push(t, 10)};
  {type.push(t, 20)};
  {type.push(t, 30)};
  TEST_TRUE( {type.contains(t, 10)} );
  TEST_TRUE( {type.contains(t, 20)} );
  TEST_TRUE( {type.contains(t, 30)} );
  TEST_FALSE( {type.contains(t, 40)} );
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

  /* remove middle */
  TEST_TRUE( {type.remove(t, 20)} );
  TEST_EQUAL( {type.size(t)}, 2 );
  TEST_EQUAL( {type.get(t, 0)}, 10 );
  TEST_EQUAL( {type.get(t, 1)}, 30 );

  /* remove front */
  TEST_TRUE( {type.remove(t, 10)} );
  TEST_EQUAL( {type.size(t)}, 1 );
  TEST_EQUAL( {type.get(t, 0)}, 30 );

  /* remove last remaining */
  TEST_TRUE( {type.remove(t, 30)} );
  TEST_TRUE( {type.empty(t)} );
  TEST_FALSE( {type.remove(t, 30)} );
""")


#
# 2. Tests for Dynamic circular buffer
#
y = Type(dtype := Dynamic("int_dcb", "int"))

dt = dtype.variable("dt")
dt2 = dtype.variable("dt2")
dr = dtype.range.variable("dr")

y.setup(f"""
  {dt.definition};
  {dtype.create(dt, 4)};
""")
y.cleanup(f"""
  {dtype.destroy(dt)};
""")

y.unit(f"{dtype.create}(): test dynamic circular buffer creation and capacity", f"""
  TEST_TRUE( {dtype.empty(dt)} );
  TEST_FALSE( {dtype.full(dt)} );
  TEST_EQUAL( {dtype.size(dt)}, 0 );
  TEST_EQUAL( {dtype.capacity(dt)}, 4 );
""")

y.unit(f"{dtype.push}(): push and overwrite on dynamic circular buffer", f"""
  {dtype.push(dt, 1)};
  {dtype.push(dt, 2)};
  {dtype.push(dt, 3)};
  {dtype.push(dt, 4)};
  TEST_TRUE( {dtype.full(dt)} );

  /* 5th element overwrites oldest (1) */
  {dtype.push(dt, 5)};
  TEST_EQUAL( {dtype.size(dt)}, 4 );
  TEST_EQUAL( {dtype.front(dt)}, 2 );
  TEST_EQUAL( {dtype.back(dt)}, 5 );
  TEST_EQUAL( {dtype.get(dt, 0)}, 2 );
  TEST_EQUAL( {dtype.get(dt, 3)}, 5 );
""")

y.unit(f"{dtype.set_capacity}(): expand capacity dynamically", f"""
  {dtype.push(dt, 10)};
  {dtype.push(dt, 20)};
  {dtype.push(dt, 30)};
  {dtype.push(dt, 40)};
  TEST_TRUE( {dtype.full(dt)} );

  /* Expand capacity from 4 to 8 */
  {dtype.set_capacity(dt, 8)};
  TEST_EQUAL( {dtype.capacity(dt)}, 8 );
  TEST_EQUAL( {dtype.size(dt)}, 4 );
  TEST_FALSE( {dtype.full(dt)} );
  TEST_EQUAL( {dtype.get(dt, 0)}, 10 );
  TEST_EQUAL( {dtype.get(dt, 1)}, 20 );
  TEST_EQUAL( {dtype.get(dt, 2)}, 30 );
  TEST_EQUAL( {dtype.get(dt, 3)}, 40 );

  /* Push 4 more without overwriting */
  {dtype.push(dt, 50)};
  {dtype.push(dt, 60)};
  {dtype.push(dt, 70)};
  {dtype.push(dt, 80)};
  TEST_TRUE( {dtype.full(dt)} );
  TEST_EQUAL( {dtype.size(dt)}, 8 );
  TEST_EQUAL( {dtype.front(dt)}, 10 );
  TEST_EQUAL( {dtype.back(dt)}, 80 );
""")

y.unit(f"{dtype.set_capacity}(): shrink capacity discarding oldest elements", f"""
  {dtype.push(dt, 10)};
  {dtype.push(dt, 20)};
  {dtype.push(dt, 30)};
  {dtype.push(dt, 40)};

  /* Shrink capacity from 4 down to 2: oldest elements (10, 20) are discarded */
  {dtype.set_capacity(dt, 2)};
  TEST_EQUAL( {dtype.capacity(dt)}, 2 );
  TEST_EQUAL( {dtype.size(dt)}, 2 );
  TEST_TRUE( {dtype.full(dt)} );
  TEST_EQUAL( {dtype.get(dt, 0)}, 30 );
  TEST_EQUAL( {dtype.get(dt, 1)}, 40 );
  TEST_EQUAL( {dtype.front(dt)}, 30 );
  TEST_EQUAL( {dtype.back(dt)}, 40 );
""")

y.unit(f"{dtype.copy}(), {dtype.move}(), {dtype.swap}(): dynamic buffer lifecycle", f"""
  {dt2.definition};
  {dtype.push(dt, 111)};
  {dtype.push(dt, 222)};

  /* Copy into uninitialized dt2 */
  {dtype.copy(dt2, dt)};
  TEST_TRUE( {dtype.equal(dt, dt2)} );
  TEST_EQUAL( {dtype.capacity(dt2)}, 4 );
  TEST_EQUAL( {dtype.size(dt2)}, 2 );
  TEST_EQUAL( {dtype.get(dt2, 0)}, 111 );
  TEST_EQUAL( {dtype.get(dt2, 1)}, 222 );
  {dtype.destroy(dt2)};

  /* Move dt into dt2 */
  {dtype.move(dt2, dt)};
  TEST_EQUAL( {dtype.size(dt2)}, 2 );
  TEST_EQUAL( {dtype.get(dt2, 0)}, 111 );
  TEST_EQUAL( {dtype.get(dt2, 1)}, 222 );
  TEST_EQUAL( {dtype.size(dt)}, 0 );

  /* Swap dt and dt2 */
  {dtype.create(dt, 6)};
  {dtype.push(dt, 999)};
  {dtype.swap(dt, dt2)};
  TEST_EQUAL( {dtype.capacity(dt)}, 4 );
  TEST_EQUAL( {dtype.size(dt)}, 2 );
  TEST_EQUAL( {dtype.front(dt)}, 111 );
  TEST_EQUAL( {dtype.capacity(dt2)}, 6 );
  TEST_EQUAL( {dtype.size(dt2)}, 1 );
  TEST_EQUAL( {dtype.front(dt2)}, 999 );

  {dtype.destroy(dt2)};
""")

y.setup(f"""
  {dt.definition};
  {dtype.create(dt, 4)};
""")
y.cleanup(f"""
  {dtype.destroy(dt)};
""")

y.unit(f"{dtype.put}()/{dtype.remove}(): dynamic container protocol addition and removal", f"""
  TEST_TRUE( {dtype.put(dt, 10)} );
  TEST_TRUE( {dtype.put(dt, 20)} );
  TEST_TRUE( {dtype.put(dt, 30)} );
  TEST_EQUAL( {dtype.size(dt)}, 3 );
  TEST_EQUAL( {dtype.get(dt, 0)}, 10 );
  TEST_EQUAL( {dtype.get(dt, 1)}, 20 );
  TEST_EQUAL( {dtype.get(dt, 2)}, 30 );

  TEST_FALSE( {dtype.remove(dt, 99)} );
  TEST_EQUAL( {dtype.size(dt)}, 3 );

  /* remove middle */
  TEST_TRUE( {dtype.remove(dt, 20)} );
  TEST_EQUAL( {dtype.size(dt)}, 2 );
  TEST_EQUAL( {dtype.get(dt, 0)}, 10 );
  TEST_EQUAL( {dtype.get(dt, 1)}, 30 );

  /* remove front */
  TEST_TRUE( {dtype.remove(dt, 10)} );
  TEST_EQUAL( {dtype.size(dt)}, 1 );
  TEST_EQUAL( {dtype.get(dt, 0)}, 30 );

  /* remove last remaining */
  TEST_TRUE( {dtype.remove(dt, 30)} );
  TEST_TRUE( {dtype.empty(dt)} );
  TEST_FALSE( {dtype.remove(dt, 30)} );
""")


# 3. Opt-out instantiation: the sort/bisect family is optional and absent when disabled
plain_type = Static("int_scb_plain", "int", 4, sorting_operations=False)
x_plain = Type(plain_type)

pt = plain_type.variable("pt")
x_plain.setup(f"""
  {pt.definition};
  {plain_type.create(pt)};
""")
x_plain.cleanup(f"""
  {plain_type.destroy(pt) if plain_type.destructible else str()};
""")

x_plain.unit(f"{plain_type.push}(): ring buffer without the sorting operations", f"""
  {plain_type.push(pt, 3)};
  {plain_type.push(pt, 1)};
  {plain_type.push(pt, 2)};
  TEST_EQUAL( {plain_type.size(pt)}, 3 );
  TEST_EQUAL( {plain_type.get(pt, 0)}, 3 );
  TEST_EQUAL( {plain_type.get(pt, 1)}, 1 );
  TEST_EQUAL( {plain_type.get(pt, 2)}, 2 );
""")
