from metac.test import *
from metac.intrusive_option import Option
from metac.test.cstring import cstring, s


# The canonical representation: position 0 is empty, position 1+ are user states
states = {
  "empty": (
    lambda e: f"{e} == INT_MIN /* EMPTY? */",
    lambda e: f"{e} = INT_MIN /* EMPTY! */",
  ),
  # The user state 1 marks a "not applicable" option distinct from the empty one
  "na": (
    lambda e: f"{e} == INT_MAX /* N/A? */",
    lambda e: f"{e} = INT_MAX /* N/A! */",
  ),
}

x = Type(type := Option("int_intrusive_option", "int", states))

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

x.unit(f"{type.create}(): fresh intrusive option is in the sentinel empty state", f"""
  TEST_EQUAL( {t}, INT_MIN );
  TEST_TRUE( {type.empty(t)} );
  TEST_FALSE( {type.primed(t)} );
  TEST_EQUAL( {type.state(t)}, 0 );
""")

x.unit(f"{type.set}(): engage with a value", f"""
  {type.set(t, 42)};
  TEST_TRUE( {type.primed(t)} );
  TEST_EQUAL( {type.value(t)}, 42 );
  TEST_EQUAL( {type.state(t)}, -1 );
""")

x.unit(f"{type.reset}(): the moved-out slot returns to the sentinel", f"""
  {type.set(t, 3)};
  {type.reset(t)};
  TEST_EQUAL( {t}, INT_MIN );
  TEST_TRUE( {type.empty(t)} );
""")

x.unit(f"{type.set_state}(): mark the user state", f"""
  {type.set(t, 5)};
  {type.set_state(t, 1)};
  TEST_EQUAL( {t}, INT_MAX );
  TEST_EQUAL( {type.state(t)}, 1 );
  TEST_FALSE( {type.empty(t)} );
  TEST_TRUE( {type.na(t)} );
  TEST_FALSE( {type.primed(t)} );
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

x.unit(f"{type.equal}(): sentinels and values compare per the state", f"""
  TEST_TRUE( {type.equal(t1, t2)} );
  {type.set(t1, 7)};
  {type.set(t2, 7)};
  TEST_TRUE( {type.equal(t1, t2)} );
  {type.set(t2, 8)};
  TEST_FALSE( {type.equal(t1, t2)} );
  {type.set_state(t2, 1)};
  TEST_FALSE( {type.equal(t1, t2)} );
""")

x.unit(f"{type.copy}(): replicate value and state", f"""
  {type.set(t1, 9)};
  {type.copy(t2, t1)};
  TEST_EQUAL( {t2}, 9 );
  TEST_TRUE( {type.equal(t1, t2)} );
  {type.set_state(t1, 1)};
  {type.copy(t2, t1)};
  TEST_EQUAL( {t2}, INT_MAX );
""")

x.unit(f"{type.move}(): transfer leaving the sentinel source", f"""
  {type.set(t1, 11)};
  {type.move(t2, t1)};
  TEST_EQUAL( {t1}, INT_MIN );
  TEST_EQUAL( {t2}, 11 );
""")

x.unit(f"{type.hash}(): equal options hash equally", f"""
  {type.set(t1, 13)};
  {type.set(t2, 13)};
  TEST_EQUAL( {type.hash(t1)}, {type.hash(t2)} );
""")

x.unit(f"{type.compare}(): empty, value and user state order", f"""
  {type.set(t1, 1)};
  {type.set_state(t2, 1)};
  TEST_TRUE( {type.compare(t2, t1)} > 0 );
  TEST_TRUE( {type.compare(t1, t2)} < 0 );
  {type.reset(t1)};
  TEST_TRUE( {type.compare(t1, t2)} < 0 );
""")


# An owning element exercises the destruction paths of the intrusive protocol
y = Type(cstr := Option(
  "cstring_intrusive_option", cstring,
  {
    "empty": (
      lambda e: f"{e} == NULL /* EMPTY? */",
      lambda e: f"{e} = NULL /* EMPTY! */",
    ),
  },
))

c = cstr.variable("c")
c1 = cstr.variable("c1")
c2 = cstr.variable("c2")


y.setup(f"""
  {c.definition};
  {cstr.create(c)};
""")
y.cleanup(f"""
  {cstr.destroy(c)};
""")

y.unit(f"{cstr.create}(): empty state is the NULL sentinel", f"""
  {cstr.create(c)};
  TEST_NULL( {c} );
  TEST_TRUE( {cstr.empty(c)} );
""")

y.unit(f"{cstr.set}(): engage with an owning value", f"""
  {cstr.set(c, s("hello"))};
  TEST_TRUE( {cstr.primed(c)} );
  {{ char* v = {cstr.value(c)}; TEST_EQUAL_CHARS( v, {s("hello")} ); cstring_free(v); }}
""")

y.unit(f"{cstr.set}(): overwrite releases the previous value", f"""
  {cstr.set(c, s("one"))};
  {cstr.set(c, s("two"))};
  {{ char* v = {cstr.value(c)}; TEST_EQUAL_CHARS( v, {s("two")} ); cstring_free(v); }}
""")

y.unit(f"{cstr.reset}(): release the value back to NULL", f"""
  {cstr.set(c, s("bye"))};
  {cstr.reset(c)};
  TEST_NULL( {c} );
  TEST_TRUE( {cstr.empty(c)} );
""")
