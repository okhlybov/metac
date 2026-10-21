from metac.test import *
from metac.string_buffer import Buffer
from metac.test.cstring import cstring, s


# Use scratch_capacity=16 so tests exercise scratch boundary crossings and chunk flushes
x = Type(type := Buffer("string_buffer", scratch_capacity=16, chunk_shift=4))

t = type.variable("t")
t2 = type.variable("t2")


x.setup(f"""
  {t.definition};
  {type.create(t)};
""")
x.cleanup(f"""
  {type.destroy(t)};
""")

x.unit(f"{type.empty}(): test freshly created empty buffer", f"""
  TEST_TRUE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 0 );
  TEST_EQUAL_CHARS( {type.view(t)}, "" );
""")

x.unit(f"{type.push_char}(): push single characters across scratch capacity", f"""
  int i;
  for(i = 0; i < 20; ++i) {{
    {type.push_char(t, "'a' + (char)i")};
  }}
  TEST_FALSE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 20 );
  TEST_EQUAL_CHARS( {type.view(t)}, "abcdefghijklmnopqrst" );
""")

x.unit(f"{type.push}(): push strings within and beyond scratch", f"""
  {type.push(t, s("hello "))};
  {type.push(t, s("world!"))};
  TEST_EQUAL( {type.size(t)}, 12 );
  TEST_EQUAL_CHARS( {type.view(t)}, "hello world!" );
  /* Appending after view */
  {type.push(t, s(" more"))};
  TEST_EQUAL( {type.size(t)}, 17 );
  TEST_EQUAL_CHARS( {type.view(t)}, "hello world! more" );
""")

x.unit(f"{type.push_slice}(): push substring slices", f"""
  {type.push_slice(t, s("prefix_1234567890_suffix"), 10)};
  TEST_EQUAL( {type.size(t)}, 10 );
  TEST_EQUAL_CHARS( {type.view(t)}, "prefix_123" );
""")

x.unit(f"{type.push_int}(): push numeric integer types", f"""
  {type.push_int(t, -42)};
  {type.push_char(t, "','")};
  {type.push_uint(t, 0)};
  {type.push_char(t, "','")};
  {type.push_uint(t, 100)};
  {type.push_char(t, "','")};
  {type.push_long(t, "-123456L")};
  {type.push_char(t, "','")};
  {type.push_ulong(t, "654321UL")};
  {type.push_char(t, "','")};
  {type.push_long(t, 0)};
  TEST_EQUAL_CHARS( {type.view(t)}, "-42,0,100,-123456,654321,0" );
""")

x.unit(f"{type.push_double}(): push floating point numbers", f"""
  {type.push_double(t, 3.14)};
  {type.push_char(t, "','")};
  {type.push_long_double(t, "2.718L")};
  TEST_EQUAL_CHARS( {type.view(t)}, "3.14,2.718" );
""")

x.unit(f"{type.push_format}(): push formatted string", f"""
  int ret;
  ret = {type.push_format(t, s("%s = %d"), s("count"), 5)};
  if(ret >= 0) {{
    TEST_EQUAL_CHARS( {type.view(t)}, "count = 5" );
  }}
""")

x.unit(f"{type.take}(): extract owned string and reset buffer", f"""
  char* str;
  {type.push(t, s("take_me"))};
  TEST_EQUAL( {type.size(t)}, 7 );
  str = {type.take(t)};
  TEST_NOT_NULL( str );
  TEST_EQUAL_CHARS( str, "take_me" );
  {cstring.destroy("str")};
  TEST_TRUE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 0 );
  TEST_EQUAL_CHARS( {type.view(t)}, "" );
""")

x.unit(f"{type.clear}(): clear buffer and reuse", f"""
  {type.push(t, s("clear_me"))};
  TEST_EQUAL( {type.size(t)}, 8 );
  {type.clear(t)};
  TEST_TRUE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 0 );
  TEST_EQUAL_CHARS( {type.view(t)}, "" );
  {type.push(t, s("reused"))};
  TEST_EQUAL( {type.size(t)}, 6 );
  TEST_EQUAL_CHARS( {type.view(t)}, "reused" );
""")


x.setup(f"""
  {t.definition};
  {t2.definition};
  {type.create(t)};
  {type.create(t2)};
""")
x.cleanup(f"""
  {type.destroy(t)};
  {type.destroy(t2)};
""")

x.unit(f"{type.copy}(): copy buffer with dirty scratch and chunks", f"""
  {type.push(t, s("very_long_string_that_exceeds_scratch_capacity_and_creates_chunks"))};
  {type.push_char(t, "'!'")};
  {type.copy(t2, t)};
  TEST_EQUAL( {type.size(t2)}, {type.size(t)} );
  TEST_EQUAL_CHARS( {type.view(t2)}, {type.view(t)} );
""")

x.unit(f"{type.move}(): move buffer to new location", f"""
  {type.push(t, s("move_content"))};
  {type.move(t2, t)};
  TEST_TRUE( {type.empty(t)} );
  TEST_EQUAL_CHARS( {type.view(t)}, "" );
  TEST_EQUAL( {type.size(t2)}, 12 );
  TEST_EQUAL_CHARS( {type.view(t2)}, "move_content" );
""")
