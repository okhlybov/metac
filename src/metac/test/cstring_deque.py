from metac.test import *
from metac.deque import Deque
from metac.test.cstring import cstring, s

x = Type(type := Deque("cstring_deque", cstring))

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
  TEST_FALSE( {type.contains(t, s("hello"))} );
""")

x.unit(f"{type.push_back}(): push to empty deque", f"""
  TEST_TRUE( {type.empty(t)} );
  {type.push_back(t, s("hello"))};
  TEST_FALSE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 1 );
  TEST_EQUAL_CHARS( {type.front_view(t)}, {s("hello")} );
  TEST_EQUAL_CHARS( {type.back_view(t)}, {s("hello")} );
""")

x.unit(f"{type.push_front}(): push to empty deque", f"""
  TEST_TRUE( {type.empty(t)} );
  {type.push_front(t, s("hello"))};
  TEST_FALSE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 1 );
  TEST_EQUAL_CHARS( {type.front_view(t)}, {s("hello")} );
  TEST_EQUAL_CHARS( {type.back_view(t)}, {s("hello")} );
""")


x.setup(f"""
  {t.definition};
  {type.create(t)};
  {type.push_back(t, s("hello"))};
""")
x.cleanup(f"""
  {type.destroy(t)};
""")

x.unit(f"{type.empty}(): test !empty deque", f"""
  TEST_FALSE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 1 );
  TEST_EQUAL_CHARS( {type.front_view(t)}, {s("hello")} );
  TEST_EQUAL_CHARS( {type.back_view(t)}, {s("hello")} );
""")

x.unit(f"{type.front_view}(): front view from !empty deque", f"""
  TEST_EQUAL_CHARS( {type.front_view(t)}, {s("hello")} );
""")

x.unit(f"{type.back_view}(): back view from !empty deque", f"""
  TEST_EQUAL_CHARS( {type.back_view(t)}, {s("hello")} );
""")

x.unit(f"{type.contains}(): contained in !empty deque", f"""
  TEST_TRUE( {type.contains(t, s("hello"))} );
""")

x.unit(f"{type.contains}(): !contained in !empty deque", f"""
  TEST_FALSE( {type.contains(t, s("Hello"))} );
""")

x.unit(f"{type.hash}(): hash !empty deque", f"""
  {type.hash(t)};
""")

x.unit(f"{type.push_front}(): push to !empty deque", f"""
  {type.push_front(t, s("world"))};
  TEST_FALSE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 2 );
  TEST_EQUAL_CHARS( {type.front_view(t)}, {s("world")} );
  TEST_EQUAL_CHARS( {type.back_view(t)}, {s("hello")} );
""")

x.unit(f"{type.push_back}(): push to !empty deque", f"""
  {type.push_back(t, s("world"))};
  TEST_FALSE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 2 );
  TEST_EQUAL_CHARS( {type.front_view(t)}, {s("hello")} );
  TEST_EQUAL_CHARS( {type.back_view(t)}, {s("world")} );
""")

x.unit(f"{type.pop_front}(): pop from !empty deque", f"""
  {type.push_front(t, s("world"))};
  char* v;
  v = {type.pop_front(t)};
  TEST_EQUAL_CHARS( v, {s("world")} );
  {cstring.destroy("v")};
  TEST_EQUAL( {type.size(t)}, 1 );
  TEST_EQUAL_CHARS( {type.front_view(t)}, {s("hello")} );
""")

x.unit(f"{type.pop_back}(): pop from !empty deque", f"""
  {type.push_back(t, s("world"))};
  char* v;
  v = {type.pop_back(t)};
  TEST_EQUAL_CHARS( v, {s("world")} );
  {cstring.destroy("v")};
  TEST_EQUAL( {type.size(t)}, 1 );
  TEST_EQUAL_CHARS( {type.back_view(t)}, {s("hello")} );
""")

x.unit(f"{type.pop_front}(): pop the only element emptying the deque", f"""
  char* v;
  v = {type.pop_front(t)};
  TEST_EQUAL_CHARS( v, {s("hello")} );
  {cstring.destroy("v")};
  TEST_TRUE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 0 );
""")

x.unit(f"{type.pop_back}(): pop the only element emptying the deque", f"""
  char* v;
  v = {type.pop_back(t)};
  TEST_EQUAL_CHARS( v, {s("hello")} );
  {cstring.destroy("v")};
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
  const char* expected[] = {{"one", "two", "three"}};
  int i = 0;
  {type.push_back(t, s("one"))};
  {type.push_back(t, s("two"))};
  {type.push_back(t, s("three"))};
  for({r} = {range.new(t)}; !{range.empty(r)}; {range.move_front(r)}) {{
    TEST_FALSE( {range.empty(r)} );
    TEST_EQUAL_CHARS( {range.front_view(r)}, expected[i++] );
  }}
  TEST_TRUE( {range.empty(r)} );
  TEST_EQUAL( i, 3 );
""")

x.unit(f"{range}(): traverse !empty deque backward", f"""
  const char* expected[] = {{"three", "two", "one"}};
  int i = 0;
  {type.push_back(t, s("one"))};
  {type.push_back(t, s("two"))};
  {type.push_back(t, s("three"))};
  for({r} = {range.new(t)}; !{range.empty(r)}; {range.move_back(r)}) {{
    TEST_FALSE( {range.empty(r)} );
    TEST_EQUAL_CHARS( {range.back_view(r)}, expected[i++] );
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
  {type.push_back(t1, s("one"))};
  {type.push_back(t1, s("two"))};
  {type.push_back(t1, s("three"))};
  {type.copy(t2, t1)};
  TEST_TRUE( {type.equal(t1, t2)} );
  TEST_EQUAL( {type.hash(t1)}, {type.hash(t2)} );
  TEST_EQUAL( {type.size(t2)}, 3 );
  TEST_EQUAL_CHARS( {type.front_view(t2)}, {s("one")} );
  TEST_EQUAL_CHARS( {type.back_view(t2)}, {s("three")} );
""")

x.setup(f"""
  {t1.definition};
  {t2.definition};
  {type.create(t1)};
  {type.create(t2)};
  {type.push_back(t1, s("one"))};
  {type.push_back(t2, s("one"))};
""")
x.cleanup(f"""
  {type.destroy(t1)};
  {type.destroy(t2)};
""")

x.unit(f"{type.equal}(): compare equal !empty deques", f"""
  TEST_TRUE( {type.equal(t1, t2)} );
""")

x.unit(f"{type.equal}(): compare !equal !empty deques of same size", f"""
  {type.push_back(t1, s("two"))};
  {type.push_back(t2, s("Three"))};
  TEST_FALSE( {type.equal(t1, t2)} );
""")


x.setup(f"""
  {t1.definition};
  {t2.definition};
  {type.create(t1)};
  {type.create(t2)};
  {type.push_back(t1, s("one"))};
""")
x.cleanup(f"""
  {type.destroy(t1)};
  {type.destroy(t2)};
""")

x.unit(f"{type.equal}(): compare !empty > empty deques", f"""
  TEST_FALSE( {type.equal(t1, t2)} );
""")
