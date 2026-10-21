from metac.test import *
from metac.queue import Queue
from metac.test.cstring import cstring, s

x = Type(type := Queue("int_queue", "int"))

t = type.variable("t")


x.setup(f"""
  {t.definition};
  {type.create(t)};
""")
x.cleanup(f"""
  {type.destroy(t)};
""")

x.unit(f"{type.empty}(): test empty queue", f"""
  TEST_TRUE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 0 );
""")

x.unit(f"{type.hash}(): hash empty queue", f"""
  TEST_TRUE( {type.empty(t)} );
  {type.hash(t)};
""")

x.unit(f"{type.contains}(): !contained in empty queue", f"""
  TEST_TRUE( {type.empty(t)} );
  TEST_FALSE( {type.contains(t, -1)} );
""")

x.unit(f"{type.enqueue}(): enqueue to empty queue", f"""
  TEST_TRUE( {type.empty(t)} );
  {type.enqueue(t, 0)};
  TEST_FALSE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 1 );
  TEST_EQUAL( {type.front(t)}, 0 );
  TEST_EQUAL( {type.back(t)}, 0 );
""")

x.unit(f"{type.copy}(): copy empty queue", f"""
  {type.variable("t2").definition};
  {type.create(type.variable("t2"))};
  {type.copy(type.variable("t2"), t)};
  TEST_TRUE( {type.equal(t, type.variable("t2"))} );
  {type.destroy(type.variable("t2"))};
""")


x.setup(f"""
  {t.definition};
  {type.create(t)};
  {type.enqueue(t, 0)};
""")
x.cleanup(f"""
  {type.destroy(t)};
""")

x.unit(f"{type.empty}(): test !empty queue", f"""
  TEST_FALSE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 1 );
  TEST_EQUAL( {type.front(t)}, 0 );
  TEST_EQUAL( {type.back(t)}, 0 );
""")

x.unit(f"{type.contains}(): !contained in !empty queue", f"""
  TEST_FALSE( {type.contains(t, -1)} );
""")

x.unit(f"{type.contains}(): contained in !empty queue", f"""
  TEST_TRUE( {type.contains(t, 0)} );
""")

x.unit(f"{type.hash}(): hash !empty queue", f"""
  {type.hash(t)};
""")

x.unit(f"{type.enqueue}(): enqueue to !empty queue", f"""
  {type.enqueue(t, 1)};
  TEST_FALSE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 2 );
  TEST_EQUAL( {type.front(t)}, 0 );
  TEST_EQUAL( {type.back(t)}, 1 );
""")

x.unit(f"{type.dequeue}(): dequeue the only element emptying the queue", f"""
  TEST_EQUAL( {type.dequeue(t)}, 0 );
  TEST_TRUE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 0 );
""")


x.setup(f"""
  {t.definition};
  {type.create(t)};
  {type.enqueue(t, 0)};
  {type.enqueue(t, 1)};
""")
x.cleanup(f"""
  {type.destroy(t)};
""")

x.unit(f"{type.dequeue}(): dequeue preserves FIFO order", f"""
  TEST_EQUAL( {type.size(t)}, 2 );
  TEST_EQUAL( {type.dequeue(t)}, 0 );
  TEST_FALSE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 1 );
  TEST_EQUAL( {type.front(t)}, 1 );
  TEST_EQUAL( {type.back(t)}, 1 );
""")

x.unit(f"{type.front}(): front peek does not dequeue", f"""
  TEST_EQUAL( {type.front(t)}, 0 );
  TEST_EQUAL( {type.size(t)}, 2 );
""")


x.setup(f"""
  {t.definition};
  {type.create(t)};
""")
x.cleanup(f"""
  {type.destroy(t)};
""")

x.unit(f"{type.enqueue}/{type.dequeue}(): FIFO over multiple elements", f"""
  {type.enqueue(t, 1)};
  {type.enqueue(t, 2)};
  {type.enqueue(t, 3)};
  TEST_EQUAL( {type.dequeue(t)}, 1 );
  TEST_EQUAL( {type.dequeue(t)}, 2 );
  TEST_EQUAL( {type.dequeue(t)}, 3 );
  TEST_TRUE( {type.empty(t)} );
""")


range = type.range
r = range.variable("r")

x.setup(f"""
  {r.definition};
  {t.definition};
  {type.create(t)};
""")
x.cleanup(f"""
  {type.destroy(t)};
""")

x.unit(f"{range}(): traverse empty queue", f"""
  for({r} = {range.new(t)}; !{range.empty(r)}; {range.move_front(r)}) {{
    TEST_FALSE( {range.empty(r)} );
  }}
  TEST_TRUE( {range.empty(r)} );
""")

x.unit(f"{range}(): traverse queue in FIFO order", f"""
  const int expected[] = {{1, 2, 3}};
  int i = 0;
  {type.enqueue(t, 1)};
  {type.enqueue(t, 2)};
  {type.enqueue(t, 3)};
  for({r} = {range.new(t)}; !{range.empty(r)}; {range.move_front(r)}) {{
    TEST_FALSE( {range.empty(r)} );
    TEST_EQUAL( {range.front(r)}, expected[i++] );
  }}
  TEST_TRUE( {range.empty(r)} );
  TEST_EQUAL( i, 3 );
""")


t1 = type.variable("t1")
t2 = type.variable("t2")

x.setup(f"""
  {t1.definition};
  {t2.definition};
  {type.create(t1)};
  {type.create(t2)};
""")
x.cleanup(f"""
  {type.destroy(t1)};
  {type.destroy(t2)};
""")

x.unit(f"{type.equal}(): compare equal empty queues", f"""
  TEST_TRUE( {type.equal(t1, t2)} );
""")

x.unit(f"{type.copy}(): copy !empty queue", f"""
  {type.enqueue(t1, 0)};
  {type.enqueue(t1, 1)};
  {type.enqueue(t1, 2)};
  {type.copy(t2, t1)};
  TEST_TRUE( {type.equal(t1, t2)} );
  TEST_EQUAL( {type.hash(t1)}, {type.hash(t2)} );
  TEST_EQUAL( {type.size(t2)}, 3 );
  TEST_EQUAL( {type.front(t2)}, 0 );
  TEST_EQUAL( {type.back(t2)}, 2 );
""")

x.setup(f"""
  {t1.definition};
  {t2.definition};
  {type.create(t1)};
  {type.create(t2)};
  {type.enqueue(t1, 3)};
  {type.enqueue(t2, 3)};
""")
x.cleanup(f"""
  {type.destroy(t1)};
  {type.destroy(t2)};
""")

x.unit(f"{type.equal}(): compare equal !empty queues", f"""
  TEST_TRUE( {type.equal(t1, t2)} );
""")

x.unit(f"{type.equal}(): compare !equal !empty queues of same size", f"""
  {type.enqueue(t1, 3)};
  {type.enqueue(t2, 4)};
  TEST_FALSE( {type.equal(t1, t2)} );
""")


x.setup(f"""
  {t1.definition};
  {t2.definition};
  {type.create(t1)};
  {type.create(t2)};
  {type.enqueue(t1, 3)};
""")
x.cleanup(f"""
  {type.destroy(t1)};
  {type.destroy(t2)};
""")

x.unit(f"{type.equal}(): compare !empty > empty queues", f"""
  TEST_FALSE( {type.equal(t1, t2)} );
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
  TEST_EQUAL( {type.front(t)}, 10 );

  TEST_FALSE( {type.remove(t, 99)} );
  TEST_EQUAL( {type.size(t)}, 3 );

  /* remove front */
  TEST_TRUE( {type.remove(t, 10)} );
  TEST_EQUAL( {type.size(t)}, 2 );
  TEST_EQUAL( {type.front(t)}, 20 );

  /* remove back */
  TEST_TRUE( {type.remove(t, 30)} );
  TEST_EQUAL( {type.size(t)}, 1 );
  TEST_EQUAL( {type.front(t)}, 20 );

  /* remove remaining */
  TEST_TRUE( {type.remove(t, 20)} );
  TEST_TRUE( {type.empty(t)} );
  TEST_FALSE( {type.remove(t, 20)} );
""")
