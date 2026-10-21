import metac.std as std
import metac.memory
from metac.string import String, _va_copy_code
from metac.tiered_vector import Vector as TieredVector
from metac.variant import Variant
from metac.core import Composite, _StructRenderer, Indirection, inout


#
class Buffer(_StructRenderer, Composite):

  brief = "Append-optimized string buffer with scratch accumulation and lazy joining"
  
  def __init__(self, name, scratch_capacity=128, chunk_shift=4, formatting_operations=True, **kwargs):
    self.formatting_operations = bool(formatting_operations)
    self.element = std.char
    self.scratch_capacity = int(scratch_capacity)
    if self.scratch_capacity < 1:
      raise ValueError(f"Scratch capacity must be at least 1, got {self.scratch_capacity}")
    self.chunk_shift = int(chunk_shift)
    
    super().__init__(name, dependencies=(std.stdlib_h, std.string_h, std.assert_h, metac.memory._allocate_code), **kwargs)
    
    self._string = String(self._decorate_component("string"), visibility="internal", formatting_operations=False)
    self._chunks = TieredVector(self._decorate_component("chunks"), self._string, chunk_shift=self.chunk_shift, visibility="internal", sorting_operations=False)
    self._variant = Variant(self._decorate_component("variant"), {"string": self._string, "chunks": self._chunks}, visibility="internal")
    
    self.dependencies.update([self._string, self._chunks, self._variant])

  def _render_struct(self, stream, header):
    super()._render_struct(stream, header)
    stream.append(f"""
      struct {self.name} {{
        {std.size_t} length; /**< @private */
        {std.size_t} scratch_size; /**< @private */
        {std.char} scratch[{self.scratch_capacity + 1}]; /**< @private */
        {self._variant} variant; /**< @private */
      }};
    """)

  @property
  def constructible(self):
    return True

  @property
  def destructible(self):
    return True

  @property
  def copyable(self):
    return True

  @property
  def moveable(self):
    return True

  @property
  def swappable(self):
    return True

  @property
  def orderable(self):
    return False

  @property
  def comparable(self):
    return False

  @property
  def hashable(self):
    return False

  def __setup__(self):
    super().__setup__()

    self.description = f"""
      Append-optimized string buffer combining an inline scratch buffer ({self.scratch_capacity} bytes)
      for fast non-allocating small appends, a tiered vector of string chunks for amortized O(1) growth,
      and lazy coalescing into a single contiguous null-terminated string on view.
    """

    with self.create as m:
      m.code = f"""
        assert(target);
        target->length = 0;
        target->scratch_size = 0;
        target->scratch[0] = '\\0';
        target->variant.tag = 0;
        target->variant.value.string = (char*)_metac_empty_string;
      """

    with self.destroy as m:
      m.code = f"""
        assert(target);
        if(target->variant.tag == 0) {{
          if(target->variant.value.string && target->variant.value.string != _metac_empty_string) {{
            free(target->variant.value.string);
          }}
        }} else if(target->variant.tag == 1) {{
          {self._chunks.destroy("(&target->variant.value.chunks)")};
        }}
      """

    with self.copy as m:
      m.code = f"""
        assert(target);
        assert(source);
        target->length = source->length;
        target->scratch_size = source->scratch_size;
        if(source->scratch_size > 0) {{
          memcpy(target->scratch, source->scratch, source->scratch_size);
        }}
        if(source->variant.tag == 0) {{
          if(source->variant.value.string && source->variant.value.string != _metac_empty_string) {{
            target->variant.value.string = {self._string.new("source->variant.value.string")};
          }} else {{
            target->variant.value.string = (char*)_metac_empty_string;
          }}
          target->variant.tag = 0;
        }} else if(source->variant.tag == 1) {{
          {self._chunks.copy("(&target->variant.value.chunks)", "(&source->variant.value.chunks)")};
          target->variant.tag = 1;
        }} else {{
          target->variant.tag = -1;
        }}
      """

    with self.move as m:
      m.inline_code = f"""
        assert(target);
        assert(source);
        *target = *source;
        {self.create("source")};
      """

    with self.method(std.size_t, "size", {"target": self}, brief="Get total length of buffer",
      description="""
        Returns the total accumulated character count in O(1) time.

        @param[in] target the string buffer to measure
        @return number of characters in the buffer
      """) as m:
      m.inline_code = """
        assert(target);
        return target->length;
      """

    with self.method(std.int, "empty", {"target": self}, brief="Check if buffer is empty",
      description="""
        Reports whether the buffer contains zero characters in O(1) time.

        @param[in] target the string buffer to check
        @return non-zero if the buffer is empty
      """) as m:
      m.inline_code = """
        assert(target);
        return target->length == 0;
      """

    with self.method(None, "clear", {"target": inout(self)}, brief="Clear buffer contents",
      description="""
        Releases any allocated memory and resets the buffer to an empty state in O(chunks) time.

        @param[in,out] target the string buffer to clear
      """) as m:
      m.code = f"""
        assert(target);
        if(target->variant.tag == 0) {{
          if(target->variant.value.string && target->variant.value.string != _metac_empty_string) {{
            free(target->variant.value.string);
          }}
        }} else if(target->variant.tag == 1) {{
          {self._chunks.destroy("(&target->variant.value.chunks)")};
        }}
        target->variant.tag = 0;
        target->variant.value.string = (char*)_metac_empty_string;
        target->length = 0;
        target->scratch_size = 0;
        target->scratch[0] = '\\0';
      """

    self._ensure_chunks = self.method(None, ("ensure", "chunks"), {"target": inout(self)}, hidden=True, visibility="internal", brief="Ensure variant is in chunks mode (internal)")
    with self._ensure_chunks as m:
      m.code = f"""
        char* old;
        assert(target);
        if(target->variant.tag == 1) return;
        if(target->variant.tag == 0) {{
          old = target->variant.value.string;
          target->variant.tag = -1;
          {self._chunks.create("(&target->variant.value.chunks)")};
          target->variant.tag = 1;
          if(old && old != _metac_empty_string && *old != '\\0') {{
            {self._chunks.push("(&target->variant.value.chunks)", "old")};
            free(old);
          }}
        }} else {{
          {self._chunks.create("(&target->variant.value.chunks)")};
          target->variant.tag = 1;
        }}
      """

    self._flush_scratch = self.method(None, ("flush", "scratch"), {"target": inout(self)}, hidden=True, visibility="internal", brief="Flush scratch buffer to chunks (internal)")
    with self._flush_scratch as m:
      m.code = f"""
        assert(target);
        if(target->scratch_size == 0) return;
        {self._ensure_chunks("target")};
        target->scratch[target->scratch_size] = '\\0';
        {self._chunks.push("(&target->variant.value.chunks)", "target->scratch")};
        target->scratch_size = 0;
      """

    with self.method(None, ("push", "slice"), {"target": inout(self), "str": Indirection(std.char, constant=True), "size": std.size_t}, brief="Push substring slice into buffer",
      description="""
        Appends `size` characters from `str` into the buffer.
        Small slices are accumulated in the scratch buffer without heap allocations.
        When scratch fills up, it is flushed into the chunk table.

        @param[in,out] target the string buffer
        @param[in] str pointer to character sequence
        @param[in] size number of characters to push
      """) as m:
      m.code = f"""
        char* chunk;
        assert(target);
        if(size == 0 || !str) return;
        target->length += size;
        if(size <= ({self.scratch_capacity} - target->scratch_size)) {{
          memcpy(target->scratch + target->scratch_size, str, size);
          target->scratch_size += size;
        }} else {{
          {self._flush_scratch("target")};
          if(size <= {self.scratch_capacity}) {{
            memcpy(target->scratch, str, size);
            target->scratch_size = size;
          }} else {{
            chunk = (char*)malloc(size + 1);
            assert(chunk);
            memcpy(chunk, str, size);
            chunk[size] = '\\0';
            {self._ensure_chunks("target")};
            {self._chunks.push("(&target->variant.value.chunks)", "chunk")};
            free(chunk);
          }}
        }}
      """

    with self.method(None, "push", {"target": inout(self), "str": Indirection(std.char, constant=True)},
      references=(self.push_slice,),
      brief="Push null-terminated string into buffer",
      description="""
        Appends a null-terminated string into the buffer.

        @param[in,out] target the string buffer
        @param[in] str null-terminated string to append
      """) as m:
      m.code = f"""
        assert(target);
        if(str) {{
          {self.push_slice("target", "str", "strlen(str)")};
        }}
      """

    with self.method(None, ("push", "char"), {"target": inout(self), "c": std.char}, brief="Push single character into buffer",
      description="""
        Appends a single character into the buffer. Fast O(1) inline scratch append.

        @param[in,out] target the string buffer
        @param[in] c character to append
      """) as m:
      m.code = f"""
        assert(target);
        if(target->scratch_size == {self.scratch_capacity}) {{
          {self._flush_scratch("target")};
        }}
        target->scratch[target->scratch_size++] = c;
        target->length += 1;
      """

    with self.method(std.int, ("push", "format", "args"), {"target": inout(self), "format": Indirection(std.char, constant=True), "args": std.va_list},
      constraint=lambda: self.formatting_operations,
      optional_group="formatting_operations",
      dependencies=(std.stdio_h, std.stdarg_h, _va_copy_code),
      brief="Push formatted output from va_list into buffer",
      description="""
        Formats the output according to the format string and va_list and appends it to the buffer.

        @param[in,out] target the string buffer
        @param[in] format the format string
        @param[in] args the variable arguments list
        @return number of characters written, or negative on encoding error

        @note This function relies on the C library `vsnprintf()` function and unconditionally returns -1 when it is missing.
      """) as m:
      m.code = f"""
        #if defined(METAC_HAS_VSNPRINTF) || defined(METAC_HAS_VSCPRINTF)
          int size;
          char stack_buf[128];
          char* buf;
          va_list args_copy;
          assert(target);
          assert(format);
          #if defined(METAC_HAS_VSCPRINTF)
            va_copy(args_copy, args);
            size = _vscprintf(format, args_copy);
            va_end(args_copy);
          #else
            va_copy(args_copy, args);
            size = vsnprintf(NULL, 0, format, args_copy);
            va_end(args_copy);
          #endif
          if(size <= 0) return size;
          if((size_t)size < sizeof(stack_buf)) {{
            buf = stack_buf;
          }} else {{
            buf = (char*)_metac_malloc((size_t)size + 1);
          }}
          #if defined(METAC_HAS_VSPRINTF_S)
            vsprintf_s(buf, (size_t)size + 1, format, args);
          #elif defined(METAC_HAS_VSNPRINTF)
            vsnprintf(buf, (size_t)size + 1, format, args);
          #else
            vsprintf(buf, format, args);
          #endif
          {self.push_slice("target", "buf", "(size_t)size")};
          if(buf != stack_buf) {{
            free(buf);
          }}
          return size;
        #else
          (void)target;
          (void)format;
          (void)args;
          assert(0 && "string buffer formatting requires vsnprintf support");
          return -1;
        #endif
      """

    with self.method(std.int, ("push", "format"), {"target": inout(self), "format": Indirection(std.char, constant=True)},
      constraint=lambda: self.formatting_operations,
      optional_group="formatting_operations",
      dependencies=(std.stdarg_h,),
      references=(self.push_format_args,),
      variadic=True,
      brief="Push formatted output into buffer",
      description="""
        Formats the output according to the format string and variable arguments and appends it to the buffer.

        @param[in,out] target the string buffer
        @param[in] format the format string
        @return number of characters written, or negative on encoding error

        @note This function relies on the C library `vsnprintf()` function and unconditionally returns -1 when it is missing.
      """) as m:
      m.code = lambda: f"""
        int size;
        va_list args;
        assert(target);
        assert(format);
        va_start(args, format);
        size = {self.push_format_args("target", "format", "args")};
        va_end(args);
        return size;
      """

    with self.method(None, ("push", "ulong"), {"target": inout(self), "value": std.unsigned_long},
      references=(self.push_slice,),
      brief="Push formatted unsigned long integer into buffer",
      description="""
        Formats the unsigned long integer and appends it to the buffer.

        @param[in,out] target the string buffer
        @param[in] value unsigned long integer value to append
      """) as m:
      m.code = lambda: f"""
        char buf[sizeof(unsigned long) * 3 + 1];
        char* p;
        unsigned long u;
        assert(target);
        p = buf + sizeof(buf);
        u = value;
        do {{
          *--p = (char)('0' + (char)(u % 10));
          u /= 10;
        }} while(u != 0);
        {self.push_slice("target", "p", "(size_t)((buf + sizeof(buf)) - p)")};
      """

    with self.method(None, ("push", "long"), {"target": inout(self), "value": std.long},
      references=(self.push_slice,),
      brief="Push formatted long integer into buffer",
      description="""
        Formats the long integer and appends it to the buffer.

        @param[in,out] target the string buffer
        @param[in] value long integer value to append
      """) as m:
      m.code = lambda: f"""
        char buf[sizeof(unsigned long) * 3 + 2];
        char* p;
        unsigned long u;
        assert(target);
        p = buf + sizeof(buf);
        if(value < 0) {{
          u = 0UL - (unsigned long)value;
        }} else {{
          u = (unsigned long)value;
        }}
        do {{
          *--p = (char)('0' + (char)(u % 10));
          u /= 10;
        }} while(u != 0);
        if(value < 0) {{
          *--p = '-';
        }}
        {self.push_slice("target", "p", "(size_t)((buf + sizeof(buf)) - p)")};
      """

    with self.method(None, ("push", "uint"), {"target": inout(self), "value": std.unsigned_int},
      references=(self.push_ulong,),
      brief="Push formatted unsigned integer into buffer",
      description="""
        Formats the unsigned integer and appends it to the buffer.

        @param[in,out] target the string buffer
        @param[in] value unsigned integer value to append
      """) as m:
      m.code = lambda: f"""
        assert(target);
        {self.push_ulong("target", "value")};
      """

    with self.method(None, ("push", "int"), {"target": inout(self), "value": std.int},
      references=(self.push_long,),
      brief="Push formatted integer into buffer",
      description="""
        Formats the integer and appends it to the buffer.

        @param[in,out] target the string buffer
        @param[in] value integer value to append
      """) as m:
      m.code = lambda: f"""
        assert(target);
        {self.push_long("target", "value")};
      """

    with self.method(None, ("push", "double"), {"target": inout(self), "value": std.double},
      constraint=lambda: self.formatting_operations,
      optional_group="formatting_operations",
      references=(self.push_format,),
      brief="Push formatted double value into buffer",
      description="""
        Formats the floating-point value and appends it to the buffer.

        @param[in,out] target the string buffer
        @param[in] value double value to append
      """) as m:
      m.code = lambda: f"""
        assert(target);
        {self.push_format("target", '"%g"', "value")};
      """

    with self.method(None, ("push", "long", "double"), {"target": inout(self), "value": std.long_double},
      constraint=lambda: self.formatting_operations,
      optional_group="formatting_operations",
      references=(self.push_format,),
      brief="Push formatted long double value into buffer",
      description="""
        Formats the long double floating-point value and appends it to the buffer.

        @param[in,out] target the string buffer
        @param[in] value long double value to append
      """) as m:
      m.code = lambda: f"""
        assert(target);
        {self.push_format("target", '"%Lg"', "value")};
      """

    with self.method(Indirection(std.char, constant=True), "view", {"target": inout(self)}, brief="Get coalesced string view",
      description="""
        Lazily coalesces all chunks and scratch into a single contiguous null-terminated
        string and returns a pointer to it. Subsequent calls without intervening pushes
        are O(1).

        @param[in,out] target the string buffer
        @return pointer to the null-terminated contiguous string
      """) as m:
      m.code = f"""
        size_t i, count, chunk_len;
        char* buf;
        char* p;
        const char* chunk;
        assert(target);
        if(target->variant.tag == 0 && target->scratch_size == 0) {{
          return target->variant.value.string ? target->variant.value.string : _metac_empty_string;
        }}
        if(target->length == 0) {{
          if(target->variant.tag == 1) {{
            {self._chunks.destroy("(&target->variant.value.chunks)")};
          }}
          target->variant.tag = 0;
          target->variant.value.string = (char*)_metac_empty_string;
          target->scratch_size = 0;
          return _metac_empty_string;
        }}
        buf = (char*)malloc(target->length + 1);
        assert(buf);
        p = buf;
        if(target->variant.tag == 1) {{
          count = target->variant.value.chunks.size;
          for(i = 0; i < count; ++i) {{
            chunk = target->variant.value.chunks.chunks[i >> {self.chunk_shift}][i & {self._chunks.chunk_mask}];
            if(chunk) {{
              chunk_len = strlen(chunk);
              memcpy(p, chunk, chunk_len);
              p += chunk_len;
            }}
          }}
          {self._chunks.destroy("(&target->variant.value.chunks)")};
        }} else if(target->variant.tag == 0) {{
          char* old = target->variant.value.string;
          if(old && old != _metac_empty_string) {{
            chunk_len = strlen(old);
            memcpy(p, old, chunk_len);
            p += chunk_len;
            free(old);
          }}
        }}
        if(target->scratch_size > 0) {{
          memcpy(p, target->scratch, target->scratch_size);
          p += target->scratch_size;
          target->scratch_size = 0;
        }}
        *p = '\\0';
        target->variant.tag = 0;
        target->variant.value.string = buf;
        return buf;
      """

    with self.method(self._string, "take", {"target": inout(self)},
      references=(self.view,),
      brief="Extract contiguous string and reset buffer",
      description="""
        Coalesces the buffer contents if needed, transfers ownership of the allocated
        string to the caller, and resets the buffer to an empty state in O(1) after coalescing.
        The returned string must be freed by string destruction or free().

        @param[in,out] target the string buffer
        @return the owned null-terminated string
      """) as m:
      m.code = f"""
        char* result;
        assert(target);
        {self.view("target")};
        result = target->variant.value.string;
        if(result == _metac_empty_string) {{
          result = (char*)malloc(1);
          assert(result);
          result[0] = '\\0';
        }}
        target->variant.tag = 0;
        target->variant.value.string = (char*)_metac_empty_string;
        target->length = 0;
        target->scratch_size = 0;
        return result;
      """
