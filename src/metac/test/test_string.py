from metac.test import *
from metac.string import String
from metac.core import Macro, out, Indirection
import metac.std as std

# Define a String type
cstring = String("test_string")

x = Type(type := cstring)

s = type.variable("s")
s2 = type.variable("s2")

x.setup(f"""
  {s.definition};
  {type.create(s)};
""")

x.cleanup(f"""
  {type.destroy(s)};
""")

x.unit(f"{type.empty}(): initial string is empty", f"""
  TEST_TRUE( {type.empty(s)} );
  TEST_EQUAL( {type.size(s)}, 0 );
  TEST_EQUAL_CHARS( {s}, "" );
""")

x.unit(f"{type.format}(): format simple text", f"""
  int n = {type.format(s, '"Hello %s!"', '"world"')};
  TEST_EQUAL( n, 12 );
  TEST_EQUAL( {type.size(s)}, 12 );
  TEST_EQUAL_CHARS( {s}, "Hello world!" );
  TEST_FALSE( {type.empty(s)} );
""")

x.unit(f"{type.format}(): format numbers and multiple specifiers", f"""
  int n = {type.format(s, '"%d + %d = %d, hex: 0x%x"', 10, 20, 30, 255)};
  TEST_TRUE( n > 0 );
  TEST_EQUAL_CHARS( {s}, "10 + 20 = 30, hex: 0xff" );
""")

x.unit(f"{type.format}(): overwrite existing formatted string", f"""
  {type.format(s, '"first: %d"', 1)};
  TEST_EQUAL_CHARS( {s}, "first: 1" );
  {type.format(s, '"second: %s"', '"overwritten"')};
  TEST_EQUAL_CHARS( {s}, "second: overwritten" );
  {type.format(s, '"third: %d %d %d"', 1, 2, 3)};
  TEST_EQUAL_CHARS( {s}, "third: 1 2 3" );
""")

x.unit(f"{type.format}(): self-referencing format argument", f"""
  {type.format(s, '"base"')};
  {type.format(s, '"[%s]"', s)};
  TEST_EQUAL_CHARS( {s}, "[base]" );
  {type.format(s, '"prefix-%s-suffix"', s)};
  TEST_EQUAL_CHARS( {s}, "prefix-[base]-suffix" );
""")

x.unit(f"{type.copy}(): copy formatted string", f"""
  {s2.definition};
  {type.create(s2)};
  {type.format(s, '"copy me %d"', 99)};
  {type.copy(s2, s)};
  TEST_TRUE( {type.equal(s, s2)} );
  TEST_EQUAL_CHARS( {s2}, "copy me 99" );
  {type.destroy(s2)};
""")

# Also test a variadic Macro directly to ensure Callable variadic support covers Macro
variadic_sprintf = Macro(
  std.int,
  {"buf": out("char*"), "fmt": Indirection(std.char, constant=True)},
  lambda buf, fmt, *args: f"sprintf({buf}, {fmt}{''.join(', ' + str(a) for a in args)})",
  variadic=True
)

x.unit("variadic Macro: custom emitter with variable arguments", f"""
  char buffer[64];
  char* pbuf = buffer;
  {variadic_sprintf("pbuf", '"%s_%d_%c"', '"test"', 123, "'Z'")};
  TEST_EQUAL_CHARS( buffer, "test_123_Z" );
""")
