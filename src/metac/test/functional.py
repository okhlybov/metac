import metac.core
from metac.test import *
from metac.module import Code


unary = metac.core.Functional("int", "unary_op", {"x": "int"}, brief="Unary function of an integer argument")
noarg = metac.core.Functional(None, "void_op", {}, brief="Function taking no arguments and returning no result")
derived = metac.core.Functional.of("derived_op", unary, brief="Unary function of an integer argument returning an integer")
internal = metac.core.Functional("int", "internal_op", {"x": "int"}, visibility="internal", brief="Unary function of an integer argument (internal)")


# Python-side sanity checks of the construction API - evaluated at the generation time
assert unary.signature == "int(int)"
assert noarg.signature == "void()"
assert derived.name == "derived_op" and derived.signature == unary.signature
assert [str(t) for t in unary.parameters.values()] == ["int"]
assert unary.result is not None and noarg.result is None
# The functional type is deliberately not orderable - relational comparison of
# distinct function pointers is unspecified in C so only the equality is defined
assert not unary.orderable
assert unary.comparable and unary.hashable
assert internal.internal
assert any("typedef int (*unary_op)(int);" in c for c in unary._header_declarations)
assert any("typedef void (*void_op)();" in c for c in noarg._header_declarations)
assert not any("internal_op" in c for c in internal._header_declarations)
assert any("typedef int (*internal_op)(int);" in c for c in internal._source_declarations)


helpers = Code(
  interface="""
    extern int functional_calls;
    METAC_STATIC_INLINE int functional_double(int x) { return x*2; }
    METAC_STATIC_INLINE int functional_negate(int x) { return -x; }
    METAC_STATIC_INLINE void functional_touch() { ++functional_calls; }
    METAC_STATIC_INLINE int functional_apply(unary_op f, int x) { return f(x); }
  """,
  implementation="""
    int functional_calls = 0;
  """,
  dependencies=(metac.core._linkage_code, unary)
)


x = Type(unary, dependencies=[helpers, noarg, derived, internal], name="functional")


f = unary.variable("f")
g = unary.variable("g")
d = derived.variable("d")
n = noarg.variable("n")
i = internal.variable("i")


x.unit("create(): null-initializes the pointer", f"""
  {f.definition};
  {unary.create(f)};
  TEST_NULL( {f} );
""")

x.unit(f"{unary}: call through a variable of the functional type", f"""
  {f.definition};
  {f} = functional_double;
  TEST_EQUAL( {f(7)}, 14 );
  {f} = functional_negate;
  TEST_EQUAL( {f(-3)}, 3 );
""")

x.unit(f"{noarg}: call a function with no parameters and void result", f"""
  {n.definition};
  functional_calls = 0;
  {n} = functional_touch;
  {n}();
  {n}();
  TEST_EQUAL( functional_calls, 2 );
""")

x.unit("apply(): pass a functional as an argument to a C function", f"""
  {f.definition};
  {f} = functional_double;
  TEST_EQUAL( functional_apply(f, 5), 10 );
  {f} = functional_negate;
  TEST_EQUAL( functional_apply(f, 5), -5 );
""")

x.unit("copy(): copy transfers the function", f"""
  {f.definition};
  {g.definition};
  {f} = functional_double;
  {unary.copy(g, f)};
  TEST_TRUE( {unary.equal(f, g)} );
  TEST_EQUAL( {g(11)}, 22 );
""")

x.unit("move(): move transfers the function leaving the source valid", f"""
  {f.definition};
  {g.definition};
  {f} = functional_negate;
  {unary.move(g, f)};
  TEST_TRUE( {unary.equal(f, g)} );
  TEST_EQUAL( {g(4)}, -4 );
""")

x.unit("equal(): compare identical and distinct functions", f"""
  {f.definition};
  {g.definition};
  {f} = functional_double;
  {g} = functional_double;
  TEST_TRUE( {unary.equal(f, g)} );
  {g} = functional_negate;
  TEST_FALSE( {unary.equal(f, g)} );
""")

x.unit("hash(): hash of the same function is stable", f"""
  {f.definition};
  {g.definition};
  {f} = functional_double;
  {unary.copy(g, f)};
  TEST_EQUAL( {unary.hash(f)}, {unary.hash(g)} );
  TEST_EQUAL( {unary.hash(f)}, {unary.hash("functional_double")} );
""")

x.unit(f"{derived}: call through a variable of the functional type derived via of()", f"""
  {d.definition};
  {d} = functional_negate;
  TEST_EQUAL( {d(9)}, -9 );
""")

x.unit(f"{internal}: internally visible functional type", f"""
  {i.definition};
  {i} = functional_double;
  TEST_EQUAL( {i(15)}, 30 );
""")