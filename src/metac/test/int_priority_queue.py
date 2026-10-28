from metac.test import *
from metac.priority_queue import Queue

x = Type(type := Queue("int_priority_queue", "int"))

t = type.variable("t")
t2 = type.variable("t2")


x.setup(f"""
  {t.definition};
""")
x.cleanup(f"""
  {type.destroy(t)};
""")

x.unit(f"{type.create}(): create empty queue", f"""
  {type.create(t)};
  TEST_TRUE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 0 );
""")

x.unit(f"{type.push}(): push into empty queue", f"""
  {type.create(t)};
  {type.push(t, 42)};
  TEST_FALSE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 1 );
  TEST_EQUAL( {type.top(t)}, 42 );
""")

x.unit(f"{type.top}(): top of the queue with the duplicates", f"""
  {type.create(t)};
  {type.push(t, 5)};
  {type.push(t, 9)};
  {type.push(t, 5)};
  {type.push(t, 9)};
  TEST_EQUAL( {type.size(t)}, 4 );
  TEST_EQUAL( {type.top(t)}, 9 );
  TEST_EQUAL( *{type.top_view(t)}, 9 );
""")

x.unit(f"{type.contains}(): contained element", f"""
  {type.create(t)};
  {type.push(t, 7)};
  TEST_TRUE( {type.contains(t, 7)} );
  TEST_FALSE( {type.contains(t, 8)} );
""")


x.setup(f"""
  int i;
  {t.definition};
  {type.create(t)};
""")
x.cleanup(f"""
  {type.destroy(t)};
""")

x.unit(f"{type.push}/{type.pop}(): pop returns the elements in the descending order", f"""
  for(i = 0; i < 100; ++i) {type.push(t, "(i*37 + 11)%100")};
  TEST_EQUAL( {type.size(t)}, 100 );
  for(i = 99; i >= 0; --i) {{
    TEST_EQUAL( {type.top(t)}, i );
    TEST_EQUAL( {type.pop(t)}, i );
  }}
  TEST_TRUE( {type.empty(t)} );
""")

x.unit(f"{type.copy}(): copy zero-capacity queue", f"""
  {t2.definition};
  {type.copy(t2, t)};
  TEST_TRUE( {type.empty(t2)} );
  TEST_EQUAL( {type.size(t2)}, 0 );
  {type.destroy(t2)};
""")

x.unit(f"{type.copy}(): copy preserves the extraction order", f"""
  {t2.definition};
  {type.create(t2)};
  for(i = 0; i < 32; ++i) {type.push(t, "(i*13 + 5)%32")};
  {type.copy(t2, t)};
  for(i = 31; i >= 0; --i) {{
    TEST_EQUAL( {type.top(t2)}, i );
    TEST_EQUAL( {type.pop(t2)}, i );
  }}
  {type.destroy(t2)};
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
  TEST_TRUE( {type.put(t, 30)} );
  TEST_TRUE( {type.put(t, 20)} );
  TEST_EQUAL( {type.size(t)}, 3 );
  TEST_EQUAL( {type.top(t)}, 30 );

  TEST_FALSE( {type.remove(t, 99)} );
  TEST_EQUAL( {type.size(t)}, 3 );

  /* remove top */
  TEST_TRUE( {type.remove(t, 30)} );
  TEST_EQUAL( {type.size(t)}, 2 );
  TEST_EQUAL( {type.top(t)}, 20 );

  /* remove leaf */
  TEST_TRUE( {type.remove(t, 10)} );
  TEST_EQUAL( {type.size(t)}, 1 );
  TEST_EQUAL( {type.top(t)}, 20 );

  /* remove last remaining */
  TEST_TRUE( {type.remove(t, 20)} );
  TEST_TRUE( {type.empty(t)} );
  TEST_FALSE( {type.remove(t, 20)} );
""")
