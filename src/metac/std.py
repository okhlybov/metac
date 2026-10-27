import re
import metac.core
from metac.core import Macro, _type_rxcache
from metac.module import Code, SystemHeader


math_h = SystemHeader("math.h")
tgmath_h = SystemHeader("tgmath.h")
limits_h = SystemHeader("limits.h")
assert_h = SystemHeader("assert.h")
stdio_h = SystemHeader("stdio.h")
stddef_h = SystemHeader("stddef.h")
string_h = SystemHeader("string.h")
stdbool_h = SystemHeader("stdbool.h")
complex_h = SystemHeader("complex.h")
inttypes_h = SystemHeader("inttypes.h")
stdint_h = SystemHeader("stdint.h")
stdarg_h = SystemHeader("stdarg.h")


stdlib_h = Code(interface="""
  #ifndef __STDC_WANT_LIB_EXT1__
    #define __STDC_WANT_LIB_EXT1__ 1
  #endif
  #if defined(METAC_MSVC) && !defined(_CRT_RAND_S)
    #define _CRT_RAND_S
  #endif
  #include <stdlib.h>
""", dependencies=(metac.core._linkage_code,))


def _primitive(name, matcher=None, cls=metac.core.Primitive, **kwargs):
  obj = cls(name, **kwargs)
  if matcher is None:
    matcher = f"^{name}$"
  _type_rxcache.append((re.compile(matcher), obj))
  return obj


bool = _primitive("_Bool", matcher=r"^(bool|_Bool)$", dependencies=(stdbool_h,))

char = _primitive("char")
signed_char = _primitive("signed char", matcher=r"^signed\s+char$")
unsigned_char = _primitive("unsigned char", matcher=r"^unsigned\s+char$")

wchar_t = _primitive("wchar_t", dependencies=(stddef_h,))

short = signed_short = short_int = signed_short_int = _primitive("short", matcher=r"^(signed\s+)?short(\s+int)?$")
unsigned_short = unsigned_short_int = _primitive("unsigned short", matcher=r"^unsigned\s+short(\s+int)?$")

int = signed = signed_int = _primitive("int", matcher=r"^(int|signed|signed\s+int)$")
unsigned = unsigned_int = _primitive("unsigned int", matcher=r"^(unsigned|unsigned\s+int)$")

long = signed_long = long_int = signed_long_int = _primitive("long", matcher=r"^(signed\s+)?long(\s+int)?$")
unsigned_long = unsigned_long_int = _primitive("unsigned long", matcher=r"^unsigned\s+long(\s+int)?$")

long_long = signed_long_long = long_long_int = signed_long_long_int = _primitive("long long", matcher=r"^(signed\s+)?long\s+long(\s+int)?$")
unsigned_long_long = unsigned_long_long_int = _primitive("unsigned long long", matcher=r"^unsigned\s+long\s+long(\s+int)?$")

size_t = _primitive("size_t", dependencies=(stddef_h,))
ptrdiff_t = _primitive("ptrdiff_t", dependencies=(stddef_h,))
uintptr_t = _primitive("uintptr_t", dependencies=(stddef_h,))
va_list = _primitive("va_list", dependencies=(stdarg_h,))

float = _primitive("float")
double = _primitive("double")
long_double = _primitive("long double", matcher=r"^long\s+double$")

float_t = _primitive("float_t", dependencies=(math_h,))
double_t = _primitive("double_t", dependencies=(math_h,))


#
class _Complex(metac.core.Primitive):
  
  def __init__(self, *args, **kwargs):
    super().__init__(*args, dependencies=(_complex_code,), **kwargs)

  def __setup__(self):
    super().__setup__()
    self.hash = Macro.of(self.hash, lambda target: f"(size_t)(creal({target})) ^ (size_t)(cimag({target}))")

  @property
  def orderable(self):
    return False


intptr_t = _primitive("intptr_t", dependencies=(inttypes_h,))
intmax_t = _primitive("intmax_t", dependencies=(inttypes_h,))
uintmax_t = _primitive("uintmax_t", dependencies=(inttypes_h,))

for bits in (8, 16, 32, 64):
  for prefix in ("int", "uint", "int_fast", "uint_fast", "int_least", "uint_least"):
    globals()[t] = _primitive(t := f"{prefix}{bits}_t", dependencies=(inttypes_h,))

 
_complex_code = Code(
  dependencies=(complex_h, tgmath_h, metac.core._linkage_code),
  interface="""
    #ifdef __cplusplus
      #include <complex>
      using metac_float_complex_t = std::complex<float>;
      using metac_double_complex_t = std::complex<double>;
      using metac_long_double_complex_t = std::complex<long double>;
    #else
      #if defined(METAC_MSVC) || defined(__TINYC__) || defined(__BORLANDC__) || defined(__TURBOC__) || defined(__DMC__) || defined(__SC__) || (defined(__LCC__) && !defined(__e2k__))
        #error This C compiler does not support C99 _Complex types. Compile as C++ or use a compiler with C99 complex support.
      #endif
      typedef float complex metac_float_complex_t;
      typedef double complex metac_double_complex_t;
      typedef long double complex metac_long_double_complex_t;
    #endif
  """
)


long_double_complex = _primitive("metac_long_double_complex_t", cls=_Complex, matcher=r"^long\s+double\s+(complex|_Complex)$")
double_complex = _primitive("metac_double_complex_t", cls=_Complex, matcher=r"^double\s+(complex|_Complex)$")
float_complex = _primitive("metac_float_complex_t", cls=_Complex, matcher=r"^float\s+(complex|_Complex)$")