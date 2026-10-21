from metac.test import *
from metac.queue import Queue
from metac.test.cstring import cstring, s

x = Type(type := Queue("cstring_queue", cstring))

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
  TEST_FALSE( {type.contains(t, s("hello"))} );
""")

x.unit(f"{type.enqueue}(): enqueue to empty queue", f"""
  TEST_TRUE( {type.empty(t)} );
  {type.enqueue(t, s("hello"))};
  TEST_FALSE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 1 );
  char* v;
  v = {type.front(t)};
  TEST_EQUAL_CHARS( v, {s("hello")} );
  {cstring.destroy("v")};
  v = {type.back(t)};
  TEST_EQUAL_CHARS( v, {s("hello")} );
  {cstring.destroy("v")};
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
  {type.enqueue(t, s("hello"))};
""")
x.cleanup(f"""
  {type.destroy(t)};
""")

x.unit(f"{type.empty}(): test !empty queue", f"""
  TEST_FALSE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 1 );
  char* v;
  v = {type.front(t)};
  TEST_EQUAL_CHARS( v, {s("hello")} );
  {cstring.destroy("v")};
  v = {type.back(t)};
  TEST_EQUAL_CHARS( v, {s("hello")} );
  {cstring.destroy("v")};
""")

x.unit(f"{type.contains}(): contained in !empty queue", f"""
  TEST_TRUE( {type.contains(t, s("hello"))} );
""")

x.unit(f"{type.contains}(): !contained in !empty queue", f"""
  TEST_FALSE( {type.contains(t, s("Hello"))} );
""")

x.unit(f"{type.hash}(): hash !empty queue", f"""
  {type.hash(t)};
""")

x.unit(f"{type.enqueue}(): enqueue to !empty queue", f"""
  {type.enqueue(t, s("world"))};
  TEST_FALSE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 2 );
  char* v;
  v = {type.front(t)};
  TEST_EQUAL_CHARS( v, {s("hello")} );
  {cstring.destroy("v")};
  v = {type.back(t)};
  TEST_EQUAL_CHARS( v, {s("world")} );
  {cstring.destroy("v")};
""")

x.unit(f"{type.dequeue}(): dequeue the only element emptying the queue", f"""
  char* v;
  v = {type.dequeue(t)};
  TEST_EQUAL_CHARS( v, {s("hello")} );
  {cstring.destroy("v")};
  TEST_TRUE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 0 );
""")


x.setup(f"""
  {t.definition};
  {type.create(t)};
""")
x.cleanup(f"""
  {type.destroy(t)};
""")

x.unit(f"{type.enqueue}/{type.dequeue}(): FIFO over multiple elements", f"""
  char* v;
  {type.enqueue(t, s("one"))};
  {type.enqueue(t, s("two"))};
  {type.enqueue(t, s("three"))};
  TEST_EQUAL( {type.size(t)}, 3 );
  v = {type.dequeue(t)};
  TEST_EQUAL_CHARS( v, {s("one")} );
  {cstring.destroy("v")};
  v = {type.dequeue(t)};
  TEST_EQUAL_CHARS( v, {s("two")} );
  {cstring.destroy("v")};
  v = {type.dequeue(t)};
  TEST_EQUAL_CHARS( v, {s("three")} );
  {cstring.destroy("v")};
  TEST_TRUE( {type.empty(t)} );
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
  {type.enqueue(t1, s("one"))};
  {type.enqueue(t1, s("two"))};
  {type.enqueue(t1, s("three"))};
  {type.copy(t2, t1)};
  TEST_TRUE( {type.equal(t1, t2)} );
  TEST_EQUAL( {type.hash(t1)}, {type.hash(t2)} );
  TEST_EQUAL( {type.size(t2)}, 3 );
  char* v;
  v = {type.front(t2)};
  TEST_EQUAL_CHARS( v, {s("one")} );
  {cstring.destroy("v")};
  v = {type.back(t2)};
  TEST_EQUAL_CHARS( v, {s("three")} );
  {cstring.destroy("v")};
""")

x.setup(f"""
  {t1.definition};
  {t2.definition};
  {type.create(t1)};
  {type.create(t2)};
  {type.enqueue(t1, s("one"))};
  {type.enqueue(t2, s("one"))};
""")
x.cleanup(f"""
  {type.destroy(t1)};
  {type.destroy(t2)};
""")

x.unit(f"{type.equal}(): compare equal !empty queues", f"""
  TEST_TRUE( {type.equal(t1, t2)} );
""")

x.unit(f"{type.equal}(): compare !equal !empty queues of same size", f"""
  {type.enqueue(t1, s("two"))};
  {type.enqueue(t2, s("Three"))};
  TEST_FALSE( {type.equal(t1, t2)} );
""")


x.setup(f"""
  {t1.definition};
  {t2.definition};
  {type.create(t1)};
  {type.create(t2)};
  {type.enqueue(t1, s("one"))};
""")
x.cleanup(f"""
  {type.destroy(t1)};
  {type.destroy(t2)};
""")

x.unit(f"{type.equal}(): compare !empty > empty queues", f"""
  TEST_FALSE( {type.equal(t1, t2)} );
""")
