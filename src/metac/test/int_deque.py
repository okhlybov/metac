from metac.test import *
from metac.deque import Deque

x = Type(type := Deque("int_deque", "int"))

t = type.variable("t")


x.setup(f"""
  {t.definition};
  {type.create(t)};
""")
x.cleanup(f"""
  {type.destroy(t)};
""")

x.unit(f"{type.empty}(): test empty deque", f"""
  TEST_TRUE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 0 );
""")

x.unit(f"{type.hash}(): hash empty deque", f"""
  TEST_TRUE( {type.empty(t)} );
  {type.hash(t)};
""")

x.unit(f"{type.contains}(): !contained in empty deque", f"""
  TEST_TRUE( {type.empty(t)} );
  TEST_FALSE( {type.contains(t, -1)} );
""")

x.unit(f"{type.push_back}(): push to empty deque", f"""
  TEST_TRUE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 0 );
  {type.push_back(t, 0)};
  TEST_FALSE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 1 );
  TEST_EQUAL( {type.front(t)}, 0 );
  TEST_EQUAL( {type.back(t)}, 0 );
""")

x.unit(f"{type.push_front}(): push to empty deque", f"""
  TEST_TRUE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 0 );
  {type.push_front(t, 0)};
  TEST_FALSE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 1 );
  TEST_EQUAL( {type.front(t)}, 0 );
  TEST_EQUAL( {type.back(t)}, 0 );
""")

x.unit(f"{type.back_view}(): back view of empty deque is never taken", f"""
  TEST_TRUE( {type.empty(t)} );
""")

x.unit(f"{type.copy}(): copy empty deque", f"""
  {type.variable("t2").definition};
  {type.create(type.variable("t2"))};
  {type.copy(type.variable("t2"), t)};
  TEST_TRUE( {type.equal(t, type.variable("t2"))} );
  {type.destroy(type.variable("t2"))};
""")


x.setup(f"""
  {t.definition};
  {type.create(t)};
  {type.push_back(t, 0)};
""")
x.cleanup(f"""
  {type.destroy(t)};
""")

x.unit(f"{type.empty}(): test !empty deque", f"""
  TEST_FALSE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 1 );
  TEST_EQUAL( {type.front(t)}, 0 );
  TEST_EQUAL( {type.back(t)}, 0 );
""")

x.unit(f"{type.front_view}(): front view from !empty deque", f"""
  TEST_EQUAL( *{type.front_view(t)}, 0 );
""")

x.unit(f"{type.back_view}(): back view from !empty deque", f"""
  TEST_EQUAL( *{type.back_view(t)}, 0 );
""")

x.unit(f"{type.contains}(): !contained in !empty deque", f"""
  TEST_FALSE( {type.contains(t, -1)} );
""")

x.unit(f"{type.contains}(): contained in !empty deque", f"""
  TEST_TRUE( {type.contains(t, 0)} );
""")

x.unit(f"{type.hash}(): hash !empty deque", f"""
  {type.hash(t)};
""")

x.unit(f"{type.push_back}(): push to !empty deque", f"""
  {type.push_back(t, 1)};
  TEST_FALSE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 2 );
  TEST_EQUAL( {type.front(t)}, 0 );
  TEST_EQUAL( {type.back(t)}, 1 );
""")

x.unit(f"{type.push_front}(): push to !empty deque", f"""
  {type.push_front(t, 1)};
  TEST_FALSE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 2 );
  TEST_EQUAL( {type.front(t)}, 1 );
  TEST_EQUAL( {type.back(t)}, 0 );
""")

x.unit(f"{type.pop_back}(): pop from !empty deque", f"""
  {type.push_front(t, 1)};
  TEST_EQUAL( {type.size(t)}, 2 );
  TEST_EQUAL( {type.pop_back(t)}, 0 );
  TEST_FALSE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 1 );
  TEST_EQUAL( {type.front(t)}, 1 );
  TEST_EQUAL( {type.back(t)}, 1 );
""")

x.unit(f"{type.pop_front}(): pop from !empty deque", f"""
  {type.push_front(t, 1)};
  TEST_EQUAL( {type.size(t)}, 2 );
  TEST_EQUAL( {type.pop_front(t)}, 1 );
  TEST_FALSE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 1 );
  TEST_EQUAL( {type.front(t)}, 0 );
  TEST_EQUAL( {type.back(t)}, 0 );
""")

x.unit(f"{type.pop_back}(): pop the only element emptying the deque", f"""
  TEST_EQUAL( {type.pop_back(t)}, 0 );
  TEST_TRUE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 0 );
""")

x.unit(f"{type.pop_front}(): pop the only element emptying the deque", f"""
  TEST_EQUAL( {type.pop_front(t)}, 0 );
  TEST_TRUE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 0 );
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

x.unit(f"{range}(): traverse empty deque", f"""
  for({r} = {range.new(t)}; !{range.empty(r)}; {range.move_front(r)}) {{
    TEST_FALSE( {range.empty(r)} );
  }}
  TEST_TRUE( {range.empty(r)} );
""")

x.unit(f"{range}(): traverse !empty deque forward", f"""
  int expected[] = {{1, 2, 3}};
  int i = 0;
  {type.push_back(t, 1)};
  {type.push_back(t, 2)};
  {type.push_back(t, 3)};
  for({r} = {range.new(t)}; !{range.empty(r)}; {range.move_front(r)}) {{
    TEST_FALSE( {range.empty(r)} );
    TEST_EQUAL( {range.front(r)}, expected[i++] );
  }}
  TEST_TRUE( {range.empty(r)} );
  TEST_EQUAL( i, 3 );
""")

x.unit(f"{range}(): traverse !empty deque backward", f"""
  int expected[] = {{3, 2, 1}};
  int i = 0;
  {type.push_back(t, 1)};
  {type.push_back(t, 2)};
  {type.push_back(t, 3)};
  for({r} = {range.new(t)}; !{range.empty(r)}; {range.move_back(r)}) {{
    TEST_FALSE( {range.empty(r)} );
    TEST_EQUAL( {range.back(r)}, expected[i++] );
  }}
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

x.unit(f"{type.equal}(): compare equal empty deques", f"""
  TEST_TRUE( {type.equal(t1, t2)} );
""")

x.unit(f"{type.copy}(): copy !empty deque", f"""
  {type.push_back(t1, 0)};
  {type.push_back(t1, 1)};
  {type.push_back(t1, 2)};
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
  {type.push_back(t1, 3)};
  {type.push_back(t2, 3)};
""")
x.cleanup(f"""
  {type.destroy(t1)};
  {type.destroy(t2)};
""")

x.unit(f"{type.equal}(): compare equal !empty deques", f"""
  TEST_TRUE( {type.equal(t1, t2)} );
""")

x.unit(f"{type.equal}(): compare !equal !empty deques of same size", f"""
  {type.push_back(t1, 3)};
  {type.push_back(t2, 4)};
  TEST_FALSE( {type.equal(t1, t2)} );
""")


x.setup(f"""
  {t1.definition};
  {t2.definition};
  {type.create(t1)};
  {type.create(t2)};
  {type.push_back(t1, 3)};
""")
x.cleanup(f"""
  {type.destroy(t1)};
  {type.destroy(t2)};
""")

x.unit(f"{type.equal}(): compare !empty > empty deques", f"""
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
  TEST_EQUAL( {type.back(t)}, 30 );

  TEST_FALSE( {type.remove(t, 99)} );
  TEST_EQUAL( {type.size(t)}, 3 );

  /* remove middle element */
  TEST_TRUE( {type.remove(t, 20)} );
  TEST_EQUAL( {type.size(t)}, 2 );
  TEST_EQUAL( {type.front(t)}, 10 );
  TEST_EQUAL( {type.back(t)}, 30 );

  /* remove front element */
  TEST_TRUE( {type.remove(t, 10)} );
  TEST_EQUAL( {type.size(t)}, 1 );
  TEST_EQUAL( {type.front(t)}, 30 );

  /* remove last remaining */
  TEST_TRUE( {type.remove(t, 30)} );
  TEST_TRUE( {type.empty(t)} );
  TEST_FALSE( {type.remove(t, 30)} );
""")
