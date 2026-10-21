import metac.core
import metac.std as std
import metac.memory
from metac.assignable import Assignable
from metac.sequential import Sequential
from metac.module import Code
from metac.range import DirectAccess
from metac.container import _Range
from metac.core import inout, Indirection, Callable, _AliasRenderer


#
class String(_AliasRenderer, Indirection, Assignable, Sequential):

  brief = "Value type wrapper of the C char* string"

  def __init__(self, name, *args, formatting_operations=True, **kwargs):
    self.formatting_operations = bool(formatting_operations)
    super().__init__(std.char, name, std.char, std.size_t, prefix=name, dependencies=(std.string_h, std.stdlib_h, metac.memory._allocate_code, _static_code), **kwargs)
    self.range = Range(self)

  def __setup__(self):
    super().__setup__()

    self.description = f"""
      Requires no constraints on the element type - the element type is fixed to `char`.
      Supports two way character traversal via the corresponding @ref {self.range} iterator
      as well as subranging with direct indexed access to the subrange's characters.

      Implemented as the dynamically sized null terminated char buffer carrying the embedded length.
      The closest C++ equivalent is [std::string<>](https://cppreference.com/cpp/string/basic_string).
    """

    self.create = self.macro_from("create", lambda target: f"{target} = (char*)_metac_empty_string")
    self.destroy = self.macro_from("destroy", lambda target: str(self.free(target)))
    self.copy = self.macro_from("copy", lambda target, source: f"{target} = {self.new(source)}")
    self.move = self.macro_from("move", lambda target, source: f"{target} = {source}, {source} = (char*)_metac_empty_string")
    self.swap = self.method(None, "swap", {"left": inout(Indirection(self)), "right": inout(Indirection(self))}, brief="Swap two strings",
      description="""
        Swaps the string buffers in O(1) by exchanging the pointers - no character copying.
        Neither string is modified content-wise beyond taking over the other's buffer.

        @param[in,out] left the first string
        @param[in,out] right the second string
      """)
    with self.swap as m:
      m.inline_code = """
        char* temp;
        temp = *left;
        *left = *right;
        *right = temp;
      """

    with self.method(Callable.Parameter(self), "new", {"source": self}, brief="Duplicate string",
      description="""
        Duplicates the string into a freshly allocated NUL-terminated buffer in O(n)
        where n is the string length, using `strdup` where available and an explicit
        `malloc`+`memcpy` fallback otherwise. A null string duplicates into the shared
        empty string which needs no release.

        @param[in] source the string to duplicate - a null string duplicates into the empty one
        @return the newly allocated copy of the string
      """) as m:
      m.code = """
        if(source) {
          #if defined(__STDC_VERSION__) && __STDC_VERSION__ >= 202311L
            return strdup(source);
          #elif defined(METAC_MSVC) || defined(__POCC__)
            return _strdup(source);
          #elif defined(__BORLANDC__) || defined(__TURBOC__) || defined(__DMC__) || defined(__SC__) || defined(__LCC__) || defined(__TINYC__)
            return strdup(source);
          #elif defined(__MINGW32__) || defined(__MINGW64__) || (defined(_POSIX_C_SOURCE) && _POSIX_C_SOURCE >= 200809L) || defined(_GNU_SOURCE) || defined(__unix__) || defined(__APPLE__)
            return strdup(source);
          #else
            size_t n = strlen(source) + 1;
            char *s = (char*)_metac_malloc(n);
            memcpy(s, source, n);
            return s;
          #endif
        } else return (char*)_metac_empty_string;
      """
      
    with self.method(None, "free", {"target": inout(self)}, brief="Free string memory",
      description="""
        Releases the buffer of a string created by `new` or assigned an owned copy.
        The empty string sentinel is never freed; the target is left pointing at it
        so the string stays usable.

        @param[in,out] target the string to release - reset to the empty string
      """) as m:
      m.inline_code = f"""
        assert(target);
        if(target != _metac_empty_string) free(target);
      """
    
    with self.set as m:
      m.inline_code = f"""
        assert(target);
        target[index] = element;
      """
      
    with self.get as m:
      m.inline_code = f"""
        assert(target);
        return target[index];
      """

    with self.view as m:
      m.inline_code = f"""
        assert(target);
        return &target[index];
      """

    with self.indexed as m:
      m.inline_code = f"""
      assert(target);
        return index < {self.size(m.target)};
      """
      
    with self.size as m:
      m.inline_code = f"""
        assert(target);
        return strlen(target);
      """
      
    with self.empty as m:
      m.inline_code = f"""
        assert(target);
        return !strlen(target);
      """
      
    with self.find_view as m:
      m.inline_code = f"""
        assert(target);
        return strchr(target, element);
      """
      
    with self.method_from("equal") as m:
      m.inline_code = f"""
        assert(left);
        assert(right);
        return strcmp(left, right) == 0;
      """

    with self.method_from("compare") as m:
      m.inline_code = f"""
        assert(left);
        assert(right);
        return strcmp(left, right);
      """
      
    with self.method_from("hash") as m:
      m.code = """
        /* the djb2a algorithm */
        char c;
        size_t hash = 5381;
        assert(target);
        while((c = *target++)) {
          c ^= (c << 5);
          hash = ((hash << 5) + hash) + c;
        }
        return hash;
      """

    with self.method(std.int, ("format", "args"), {"target": inout(Indirection(self)), "format": Indirection(std.char, constant=True), "args": std.va_list},
      constraint=lambda: self.formatting_operations,
      optional_group="formatting_operations",
      dependencies=(std.stdio_h, std.stdarg_h, _va_copy_code),
      brief="Format output into string from va_list",
      description="""
        Formats the output according to the format string and variable arguments list,
        replacing the previous contents of target. The target string buffer is allocated
        dynamically to fit the formatted output. Any previous buffer held by target is freed.

        @param[in,out] target the string to format into
        @param[in] format the format string
        @param[in] args the variable arguments list
        @return number of characters written, or negative on encoding error
        
        @note This function relies on the C library `vsnprintf` function and unconditionally returns -1 when it is missing.
      """) as m:
      m.code = """
        #if defined(METAC_HAS_VSNPRINTF) || defined(METAC_HAS_VSCPRINTF)
          int len;
          char* buf;
          va_list args_copy;
          assert(target);
          assert(format);
          #if defined(METAC_HAS_VSCPRINTF)
            va_copy(args_copy, args);
            len = _vscprintf(format, args_copy);
            va_end(args_copy);
          #else
            va_copy(args_copy, args);
            len = vsnprintf(NULL, 0, format, args_copy);
            va_end(args_copy);
          #endif
          if(len < 0) return len;
          buf = (char*)_metac_malloc((size_t)len + 1);
          #if defined(METAC_HAS_VSPRINTF_S)
            vsprintf_s(buf, (size_t)len + 1, format, args);
          #elif defined(METAC_HAS_VSNPRINTF)
            vsnprintf(buf, (size_t)len + 1, format, args);
          #else
            vsprintf(buf, format, args);
          #endif
          if(*target && *target != _metac_empty_string) {
            free(*target);
          }
          *target = buf;
          return len;
        #else
          (void)target;
          (void)format;
          (void)args;
          assert(0 && "string formatting requires vsnprintf() support");
          return -1;
        #endif
      """

    with self.method(std.int, "format", {"target": inout(Indirection(self)), "format": Indirection(std.char, constant=True)},
      constraint=lambda: self.formatting_operations,
      optional_group="formatting_operations",
      dependencies=(std.stdarg_h,),
      references=(self.format_args,),
      variadic=True,
      brief="Format output into string",
      description="""
        Formats the output according to the format string and variable arguments,
        replacing the previous contents of target. The target string buffer is allocated
        dynamically to fit the formatted output. Any previous buffer held by target is freed.

        @param[in,out] target the string to format into
        @param[in] format the format string
        @return number of characters written, or negative on encoding error

        @note This function relies on the C library `vsnprintf` function and unconditionally returns -1 when it is missing.
      """) as m:
      m.code = lambda: f"""
        int len;
        va_list args;
        assert(target);
        assert(format);
        va_start(args, format);
        len = {self.format_args("target", "format", "args")};
        va_end(args);
        return len;
      """

  @property
  def rvalue_type(self):
    return self

  @property
  def lvalue_type(self):
    return self

  @property
  def destructible(self):
    return True
  
  
_static_code = Code(dependencies=(metac.core._linkage_code,), interface=f"""
  /** @private */
  METAC_EXTERN const char* _metac_empty_string;
""", implementation=f"""
  const char* _metac_empty_string = "";
""")


_va_copy_code = Code(dependencies=(std.stdarg_h, std.stdio_h, std.string_h, metac.core._linkage_code), definitions="""
  #ifndef va_copy
    #if defined(__GNUC__) || defined(__clang__) || defined(__TINYC__)
      #define va_copy(d, s) __builtin_va_copy(d, s)
    #elif defined(__va_copy)
      #define va_copy(d, s) __va_copy(d, s)
    #elif defined(__POCC__) || defined(METAC_MSVC) || defined(__BORLANDC__) || defined(__TURBOC__) || defined(__DMC__) || defined(__SC__) || defined(__LCC__)
      #define va_copy(d, s) ((d) = (s))
    #else
      #define va_copy(d, s) memcpy(&(d), &(s), sizeof(va_list))
    #endif
  #endif
""")


#
class Range(_Range, DirectAccess):
  brief = "Direct access range over the string characters"

  
  def _render_struct(self, stream, header):
    super()._render_struct(stream, header)
    stream.append(f"""
      struct {self.name} {{
        {Indirection(self.iterable.type, constant=True)} iterable; /**< @private */
        {self.iterable.index} front, back; /**< @private */
      }};
    """)

  def __setup__(self):
    super().__setup__()

    with self.method(Callable.Parameter(self), "new", {"iterable" : self.iterable}, brief="Create the range spanning the whole string",
      description="""
        Creates the range over the characters up to but not including the terminator.
        The range must not outlive the string buffer.

        @param[in] iterable the string to span
        @return the range covering the whole string
      """) as m:
      m.inline_code = lambda: f"""
        {self} result;
        assert(iterable);
        result.iterable = iterable;
        result.front = 0;
        result.back = {self.iterable.size("iterable")};
        return result;
      """

    with self.empty as m:
      m.inline_code = f"""
        assert(target);
        return target->front >= target->back;
      """

    with self.front as m:
      m.inline_code = lambda: f"""
        assert(target);
        assert(!{self.empty(m.target)});
        return {self.iterable.get("target->iterable", "target->front")};
      """

    with self.front_view as m:
      m.inline_code = lambda: f"""
        assert(target);
        assert(!{self.empty(m.target)});
        return {self.iterable.view("target->iterable", "target->front")};
      """

    with self.move_front as m:
      m.inline_code = f"""
        assert(target);
        assert(!{self.empty(m.target)});
        ++target->front;
      """

    with self.back as m:
      m.inline_code = lambda: f"""
        assert(target);
        assert(!{self.empty(m.target)});
        return {self.iterable.get("target->iterable", "target->back-1")};
      """

    with self.back_view as m:
      m.inline_code = lambda: f"""
        assert(target);
        assert(!{self.empty(m.target)});
        return {self.iterable.view("target->iterable", "target->back-1")};
      """

    with self.move_back as m:
      m.inline_code = f"""
        assert(target);
        assert(!{self.empty(m.target)});
        --target->back;
      """

    with self.get as m:
      m.inline_code = lambda: f"""
      assert(target);
      return {self.iterable.get("target->iterable", "target->front + index")};
    """

    with self.view as m:
      m.inline_code = lambda: f"""
        assert(target);
        return {self.iterable.view("target->iterable", "target->front + index")};
      """

    with self.size as m:
      m.inline_code = f"""
        assert(target);
        assert(target->back >= target->front);
        return target->back - target->front;
      """  