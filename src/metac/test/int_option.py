from metac.test import *
from metac.option import Option
from metac.vector import Vector


x = Type(type := Option("int_option", "int"))

t = type.variable("t")
t1 = type.variable("t1")
t2 = type.variable("t2")


x.setup(f"""
  {t.definition};
  {type.create(t)};
""")
x.cleanup(f"""
  {type.destroy(t) if type.destructible else str()}
""")

x.unit(f"{type.create}(): fresh option is empty and holds no value", f"""
  TEST_TRUE( {type.empty(t)} );
  TEST_FALSE( {type.primed(t)} );
  TEST_EQUAL( {type.state(t)}, 0 );
""")

x.unit(f"{type.set}(): engage with a value", f"""
  {type.set(t, 42)};
  TEST_TRUE( {type.primed(t)} );
  TEST_FALSE( {type.empty(t)} );
  TEST_EQUAL( {type.value(t)}, 42 );
  TEST_EQUAL( {type.state(t)}, -1 );
""")

x.unit(f"{type.set}(): overwrite the held value", f"""
  {type.set(t, 1)};
  {type.set(t, 2)};
  TEST_EQUAL( {type.value(t)}, 2 );
  TEST_EQUAL( {type.state(t)}, -1 );
""")

x.unit(f"{type.value_view}(): view the held value", f"""
  {type.set(t, 7)};
  TEST_EQUAL( *{type.value_view(t)}, 7 );
""")

x.unit(f"{type.reset}(): back to the empty state", f"""
  {type.set(t, 3)};
  {type.reset(t)};
  TEST_TRUE( {type.empty(t)} );
  TEST_FALSE( {type.primed(t)} );
  TEST_EQUAL( {type.state(t)}, 0 );
""")

x.unit(f"{type.emplace}(): construct in place", f"""
  {type.emplace(t)};
  TEST_TRUE( {type.primed(t)} );
  TEST_EQUAL( {type.value(t)}, 0 );
""")


x.setup(f"""
  {t1.definition};
  {t2.definition};
  {type.create(t1)};
  {type.create(t2)};
""")
x.cleanup(f"""
  {type.destroy(t1) if type.destructible else str()}
  {type.destroy(t2) if type.destructible else str()}
""")

x.unit(f"{type.equal}(): empty options are equal", f"""
  TEST_TRUE( {type.equal(t1, t2)} );
""")

x.unit(f"{type.equal}(): engaged options compare by value", f"""
  {type.set(t1, 5)};
  {type.set(t2, 5)};
  TEST_TRUE( {type.equal(t1, t2)} );
  {type.set(t2, 6)};
  TEST_FALSE( {type.equal(t1, t2)} );
""")

x.unit(f"{type.equal}(): empty differs from engaged", f"""
  {type.set(t2, 5)};
  TEST_FALSE( {type.equal(t1, t2)} );
""")

x.unit(f"{type.copy}(): replicate the state and value", f"""
  {type.set(t1, 9)};
  {type.copy(t2, t1)};
  TEST_TRUE( {type.equal(t1, t2)} );
  TEST_EQUAL( {type.value(t2)}, 9 );
""")

x.unit(f"{type.move}(): transfer leaving the empty source", f"""
  {type.set(t1, 11)};
  {type.move(t2, t1)};
  TEST_TRUE( {type.empty(t1)} );
  TEST_EQUAL( {type.value(t2)}, 11 );
""")

x.unit(f"{type.swap}(): exchange the contents", f"""
  {type.set(t1, 1)};
  {type.set(t2, 2)};
  {type.swap(t1, t2)};
  TEST_EQUAL( {type.value(t1)}, 2 );
  TEST_EQUAL( {type.value(t2)}, 1 );
""")

x.unit(f"{type.hash}(): equal options hash equally", f"""
  {type.set(t1, 13)};
  {type.set(t2, 13)};
  TEST_EQUAL( {type.hash(t1)}, {type.hash(t2)} );
""")

x.unit(f"{type.compare}(): empty orders before engaged", f"""
  {type.set(t2, 1)};
  TEST_TRUE( {type.compare(t1, t2)} < 0 );
  TEST_TRUE( {type.compare(t2, t1)} > 0 );
  TEST_EQUAL( {type.compare(t1, t1)}, 0 );
""")


# A multistate option: states 1 and 2 carry user-defined meaning
y = Type(multi := Option("int_state_option", "int", states=3))

m = multi.variable("m")


y.setup(f"""
  {m.definition};
  {multi.create(m)};
""")
y.cleanup(f"""
  {multi.destroy(m) if multi.destructible else str()}
""")

y.unit(f"{multi.set_state}(): transition to a user state", f"""
  {multi.set(m, 5)};
  {multi.set_state(m, 1)};
  TEST_FALSE( {multi.empty(m)} );
  TEST_FALSE( {multi.primed(m)} );
  TEST_EQUAL( {multi.state(m)}, 1 );
""")

y.unit(f"{multi.set_state}(): the empty state is reachable", f"""
  {multi.set_state(m, 2)};
  TEST_EQUAL( {multi.state(m)}, 2 );
  {multi.set_state(m, 0)};
  TEST_TRUE( {multi.empty(m)} );
""")

y.unit(f"{multi.reset}(): user states reset to empty as well", f"""
  {multi.set_state(m, 1)};
  {multi.reset(m)};
  TEST_TRUE( {multi.empty(m)} );
""")


# Options compose as container elements through the value protocol
v = Type(vec := Vector("int_option_vector", type))

vt = vec.variable("vt")

v.setup(f"""
  {vt.definition};
  {t.definition};
  {vec.create(vt)};
  {type.create(t)};
""")
v.cleanup(f"""
  {vec.destroy(vt)};
  {type.destroy(t) if type.destructible else str()}
""")

v.unit(f"{vec.push}(): options as vector elements", f"""
  {type.set(t, 21)};
  {vec.push(vt, t)};
  {type.set(t, 22)};
  {vec.push(vt, t)};
  {type.reset(t)};
  {vec.push(vt, t)};
  TEST_EQUAL( {vec.size(vt)}, 3 );
  TEST_TRUE( {type.primed(vec.view(vt, 0))} );
  TEST_TRUE( {type.primed(vec.view(vt, 1))} );
  TEST_TRUE( {type.empty(vec.view(vt, 2))} );
""")
