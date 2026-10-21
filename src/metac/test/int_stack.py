from metac.test import *
from metac.stack import Stack

x = Type(type := Stack("int_stack", "int"))

t = type.variable("t")


x.setup(f"""
  {t.definition};
  {type.create(t)};
""")
x.cleanup(f"""
  {type.destroy(t)};
""")

x.unit(f"{type.empty}(): test empty stack", f"""
  TEST_TRUE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 0 );
""")

x.unit(f"{type.hash}(): hash empty stack", f"""
  TEST_TRUE( {type.empty(t)} );
  {type.hash(t)};
""")

x.unit(f"{type.contains}(): !contained in empty stack", f"""
  TEST_TRUE( {type.empty(t)} );
  TEST_FALSE( {type.contains(t, -1)} );
""")

x.unit(f"{type.push}(): push to empty stack", f"""
  TEST_TRUE( {type.empty(t)} );
  {type.push(t, 0)};
  TEST_FALSE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 1 );
  TEST_EQUAL( {type.top(t)}, 0 );
""")

x.unit(f"{type.copy}(): copy empty stack", f"""
  {type.variable("t2").definition};
  {type.create(type.variable("t2"))};
  {type.copy(type.variable("t2"), t)};
  TEST_TRUE( {type.equal(t, type.variable("t2"))} );
  {type.destroy(type.variable("t2"))};
""")


x.setup(f"""
  {t.definition};
  {type.create(t)};
  {type.push(t, 0)};
""")
x.cleanup(f"""
  {type.destroy(t)};
""")

x.unit(f"{type.empty}(): test !empty stack", f"""
  TEST_FALSE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 1 );
  TEST_EQUAL( {type.top(t)}, 0 );
""")

x.unit(f"{type.contains}(): !contained in !empty stack", f"""
  TEST_FALSE( {type.contains(t, -1)} );
""")

x.unit(f"{type.contains}(): contained in !empty stack", f"""
  TEST_TRUE( {type.contains(t, 0)} );
""")

x.unit(f"{type.hash}(): hash !empty stack", f"""
  {type.hash(t)};
""")

x.unit(f"{type.push}(): push to !empty stack", f"""
  {type.push(t, 1)};
  TEST_FALSE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 2 );
  TEST_EQUAL( {type.top(t)}, 1 );
""")

x.unit(f"{type.pop}(): pop the only element emptying the stack", f"""
  TEST_EQUAL( {type.pop(t)}, 0 );
  TEST_TRUE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 0 );
""")


x.setup(f"""
  {t.definition};
  {type.create(t)};
  {type.push(t, 0)};
  {type.push(t, 1)};
""")
x.cleanup(f"""
  {type.destroy(t)};
""")

x.unit(f"{type.pop}(): pop preserves LIFO order", f"""
  TEST_EQUAL( {type.size(t)}, 2 );
  TEST_EQUAL( {type.pop(t)}, 1 );
  TEST_FALSE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 1 );
  TEST_EQUAL( {type.top(t)}, 0 );
""")

x.unit(f"{type.top}(): top peek does not pop", f"""
  TEST_EQUAL( {type.top(t)}, 1 );
  TEST_EQUAL( {type.size(t)}, 2 );
""")


x.setup(f"""
  {t.definition};
  {type.create(t)};
""")
x.cleanup(f"""
  {type.destroy(t)};
""")

x.unit(f"{type.push}/{type.pop}(): LIFO over multiple elements", f"""
  {type.push(t, 1)};
  {type.push(t, 2)};
  {type.push(t, 3)};
  TEST_EQUAL( {type.pop(t)}, 3 );
  TEST_EQUAL( {type.pop(t)}, 2 );
  TEST_EQUAL( {type.pop(t)}, 1 );
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

x.unit(f"{range}(): traverse empty stack", f"""
  for({r} = {range.new(t)}; !{range.empty(r)}; {range.move_front(r)}) {{
    TEST_FALSE( {range.empty(r)} );
  }}
  TEST_TRUE( {range.empty(r)} );
""")

x.unit(f"{range}(): traverse stack in LIFO order", f"""
  const int expected[] = {{3, 2, 1}};
  int i = 0;
  {type.push(t, 1)};
  {type.push(t, 2)};
  {type.push(t, 3)};
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

x.unit(f"{type.equal}(): compare equal empty stacks", f"""
  TEST_TRUE( {type.equal(t1, t2)} );
""")

x.unit(f"{type.copy}(): copy !empty stack", f"""
  {type.push(t1, 0)};
  {type.push(t1, 1)};
  {type.push(t1, 2)};
  {type.copy(t2, t1)};
  TEST_TRUE( {type.equal(t1, t2)} );
  TEST_EQUAL( {type.hash(t1)}, {type.hash(t2)} );
  TEST_EQUAL( {type.size(t2)}, 3 );
  TEST_EQUAL( {type.top(t2)}, 2 );
""")

x.setup(f"""
  {t1.definition};
  {t2.definition};
  {type.create(t1)};
  {type.create(t2)};
  {type.push(t1, 3)};
  {type.push(t2, 3)};
""")
x.cleanup(f"""
  {type.destroy(t1)};
  {type.destroy(t2)};
""")

x.unit(f"{type.equal}(): compare equal !empty stacks", f"""
  TEST_TRUE( {type.equal(t1, t2)} );
""")

x.unit(f"{type.equal}(): compare !equal !empty stacks of same size", f"""
  {type.push(t1, 3)};
  {type.push(t2, 4)};
  TEST_FALSE( {type.equal(t1, t2)} );
""")


x.setup(f"""
  {t1.definition};
  {t2.definition};
  {type.create(t1)};
  {type.create(t2)};
  {type.push(t1, 3)};
""")
x.cleanup(f"""
  {type.destroy(t1)};
  {type.destroy(t2)};
""")

x.unit(f"{type.equal}(): compare !empty > empty stacks", f"""
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
  TEST_EQUAL( {type.top(t)}, 30 );

  TEST_FALSE( {type.remove(t, 99)} );
  TEST_EQUAL( {type.size(t)}, 3 );

  /* remove top */
  TEST_TRUE( {type.remove(t, 30)} );
  TEST_EQUAL( {type.size(t)}, 2 );
  TEST_EQUAL( {type.top(t)}, 20 );

  /* remove bottom */
  TEST_TRUE( {type.remove(t, 10)} );
  TEST_EQUAL( {type.size(t)}, 1 );
  TEST_EQUAL( {type.top(t)}, 20 );

  /* remove remaining */
  TEST_TRUE( {type.remove(t, 20)} );
  TEST_TRUE( {type.empty(t)} );
  TEST_FALSE( {type.remove(t, 20)} );
""")