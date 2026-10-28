from metac.test import *
from metac.list import List

x = Type(type := List("int_list", "int"))

t = type.variable("t")


x.setup(f"""
  {t.definition};
  {type.create(t)};
""")
x.cleanup(f"""
  {type.destroy(t)};
""")

x.unit(f"{type.empty}(): test empty list", f"""
  TEST_TRUE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 0 );
""")

x.unit(f"{type.hash}(): hash empty list", f"""
  TEST_TRUE( {type.empty(t)} );
  {type.hash(t)};
""")

x.unit(f"{type.contains}(): !contained in empty list", f"""
  TEST_TRUE( {type.empty(t)} );
  TEST_FALSE( {type.contains(t, -1)} );
""")

x.unit(f"{type.front}(): front peek from !empty list", f"""
  {type.push_front(t, 0)};
  TEST_FALSE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 1 );
  TEST_EQUAL( {type.front(t)}, 0 );
""")

x.unit(f"{type.front_view}(): front view from !empty list", f"""
  {type.push_front(t, 0)};
  TEST_FALSE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 1 );
  TEST_EQUAL( *{type.front_view(t)}, 0 );
""")

x.unit(f"{type.push_front}(): push to empty list", f"""
  TEST_TRUE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 0 );
  {type.push_front(t, 0)};
  TEST_FALSE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 1 );
""")


x.setup(f"""
  {t.definition};
  {type.create(t)};
  {type.push_front(t, 0)};
""")
x.cleanup(f"""
  {type.destroy(t)};
""")

x.unit(f"{type.empty}(): test !empty list", f"""
  TEST_FALSE( {type.empty(t)} );
  TEST_EQUAL( {type.front(t)}, 0 );
""")

x.unit(f"{type.contains}(): !contained in !empty list", f"""
  TEST_FALSE( {type.empty(t)} );
  TEST_FALSE( {type.contains(t, -1)} );
""")

x.unit(f"{type.contains}(): contained in !empty list", f"""
  TEST_FALSE( {type.empty(t)} );
  TEST_TRUE( {type.contains(t, 0)} );
""")

x.unit(f"{type.hash}(): hash !empty list", f"""
  TEST_FALSE( {type.empty(t)} );
  {type.hash(t)};
""")

x.unit(f"{type.push_front}(): push to !empty list", f"""
  TEST_FALSE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 1 );
  {type.push_front(t, 1)};
  TEST_FALSE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 2 );
""")

x.unit(f"{type.pop_front}(): pop from !empty list", f"""
  TEST_FALSE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 1 );
  TEST_EQUAL( {type.front(t)}, 0 );
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

x.unit(f"{range}(): traverse empty list", f"""
  for({r} = {range.new(t)}; !{range.empty(r)}; {range.move_front(r)}) {{
    TEST_FALSE( {range.empty(r)} );
  }}
  TEST_TRUE( {range.empty(r)} );
""")

x.unit(f"{range}(): traverse !empty list", f"""
  {type.push_front(t, -1)};
  for({r} = {range.new(t)}; !{range.empty(r)}; {range.move_front(r)}) {{
    TEST_FALSE( {range.empty(r)} );
    TEST_EQUAL( {range.front(r)}, -1 );
  }}
  TEST_TRUE( {range.empty(r)} );
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

x.unit(f"{type.equal}(): compare equal empty lists", f"""
    TEST_TRUE( {type.equal(t1, t2)} );
""")


x.setup(f"""
  {t1.definition};
  {t2.definition};
  {type.create(t1)};
  {type.create(t2)};
  {type.push_front(t1, 3)};
  {type.push_front(t2, 3)};
""")
x.cleanup(f"""
  {type.destroy(t1)};
  {type.destroy(t2)};
""")

x.unit(f"{type.equal}(): compare equal !empty lists", f"""
    TEST_TRUE( {type.equal(t1, t2)} );
    TEST_EQUAL( {type.hash(t1)}, {type.hash(t2)} );
""")

x.unit(f"{type.equal}(): compare !equal !empty lists of same size", f"""
  {type.push_front(t1, 3)};
  {type.push_front(t2, 4)};
    TEST_FALSE( {type.equal(t1, t2)} );
""")


x.setup(f"""
  {t1.definition};
  {t2.definition};
  {type.create(t1)};
  {type.create(t2)};
  {type.push_front(t1, 3)};
""")
x.cleanup(f"""
  {type.destroy(t1)};
  {type.destroy(t2)};
""")

x.unit(f"{type.equal}(): compare !empty > empty lists", f"""
    TEST_FALSE( {type.equal(t1, t2)} );
""")


x.setup(f"""
  {t1.definition};
  {t2.definition};
  {type.create(t1)};
  {type.create(t2)};
  {type.push_front(t1, 3)};
  {type.push_front(t2, 3)};
  {type.push_front(t2, 4)};
""")
x.cleanup(f"""
  {type.destroy(t1)};
  {type.destroy(t2)};
""")

x.unit(f"{type.equal}(): compare !empty < !empty lists", f"""
  TEST_FALSE( {type.equal(t1, t2)} );
""")


x.setup(f"""
  {t1.definition};
  {t2.definition};
  {type.create(t1)};
""")
x.cleanup(f"""
  {type.destroy(t1)};
  {type.destroy(t2)};
""")

x.unit(f"{type.copy}(): copy empty list", f"""
  {type.copy(t2, t1)};
""")

x.unit(f"{type.copy}(): copy !empty list", f"""
  {type.push_front(t1, 0)};
  {type.push_front(t1, 1)};
  {type.push_front(t1, 2)};
  {type.copy(t2, t1)};
  TEST_TRUE( {type.equal(t1, t2)} );
""")

x.unit(f"{type.copy}(): self-copy does not corrupt list", f"""
  {type.copy(t2, t1)};
  {type.push_front(t1, 10)};
  {type.push_front(t1, 20)};
  {type.copy(t1, t1)};
  TEST_EQUAL( {type.size(t1)}, 2 );
  TEST_EQUAL( {type.front(t1)}, 20 );
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
  TEST_EQUAL( {type.front(t)}, 30 );

  TEST_FALSE( {type.remove(t, 99)} );
  TEST_EQUAL( {type.size(t)}, 3 );

  /* remove middle element */
  TEST_TRUE( {type.remove(t, 20)} );
  TEST_EQUAL( {type.size(t)}, 2 );

  /* remove front element */
  TEST_TRUE( {type.remove(t, 30)} );
  TEST_EQUAL( {type.size(t)}, 1 );
  TEST_EQUAL( {type.front(t)}, 10 );

  /* remove last remaining */
  TEST_TRUE( {type.remove(t, 10)} );
  TEST_TRUE( {type.empty(t)} );
  TEST_FALSE( {type.remove(t, 10)} );
""")