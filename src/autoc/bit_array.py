import autoc.std as std
from autoc.hash import XorRot
from autoc.core import inout, out, Composite, _StructRenderer


# Fixed-size stack-allocated bit array with set algebra operations
class Array(_StructRenderer, Composite):

  brief = "Fixed-size bit array with set algebra operations"

  def __init__(self, name, capacity, *args, algebraic_operations=True, hasher=XorRot(), dependencies=(), **kwargs):
    self.algebraic_operations = bool(algebraic_operations)
    self._capacity = int(capacity)
    if self._capacity < 1:
      raise ValueError(f"Array capacity must be at least 1, got {self._capacity}")
    self._word_count = (self._capacity + 7) // 8
    self._tail_bits = self._capacity % 8
    self._tail_mask = (1 << self._tail_bits) - 1 if self._tail_bits else 0xFF
    super().__init__(name, *args, dependencies=(*dependencies, std.assert_h, std.string_h, hasher), **kwargs)
    self.hasher = hasher

  @property
  def destructible(self):
    return False

  @property
  def orderable(self):
    return False

  @property
  def zero_initializable(self):
    return True

  def __setup__(self):
    super().__setup__()

    self.description = f"""
      Fixed-size bit array of {self._capacity} bits stored inline as {self._word_count} byte(s).

      This is a value type: no heap allocation, trivially copyable and moveable.
      The unused trailing bits in the last byte are always kept at zero so
      equality comparison and hashing are consistent.
    """

    # --- value protocol ---

    with self.create as m:
      m.inline_code = f"""
        assert(target);
        memset(target->words, 0, {self._word_count});
      """

    with self.copy as m:
      m.inline_code = f"""
        assert(target);
        assert(source);
        memcpy(target->words, source->words, {self._word_count});
      """

    with self.equal as m:
      m.inline_code = f"""
        assert(left);
        assert(right);
        return memcmp(left->words, right->words, {self._word_count}) == 0;
      """

    with self.hash as m:
      def _hash(m):
        state = self.hasher.state_t.variable("state")
        return f"""
          size_t result, index;
          {state.definition};
          assert(target);
          {self.hasher.create(state)};
          for(index = 0; index < {self._word_count}; ++index) {{
            {self.hasher.update(state, "(size_t)target->words[index]")};
          }}
          result = {self.hasher.hash(state)};
          {self.hasher.destroy(state)};
          return result;
        """
      m.code = _hash

    # --- queries ---

    with self.method(std.size_t, "capacity", {"target": self},
      brief="Get the total number of bits",
      description=f"""
        Returns the fixed capacity of the bit array ({self._capacity}).

        @param[in] target the bit array
        @return the total number of bits
      """) as m:
      m.inline_code = f"""
        assert(target);
        (void)target;
        return {self._capacity};
      """

    with self.method(std.size_t, "count", {"target": self},
      brief="Count the number of set bits",
      description="""
        Counts the number of bits in the array that are set to 1 (population count).

        @param[in] target the bit array
        @return the number of set bits
      """) as m:
      m.code = f"""
        size_t index, count = 0;
        unsigned char b;
        assert(target);
        for(index = 0; index < {self._word_count}; ++index) {{
          b = target->words[index];
          while(b) {{ b &= b - 1; ++count; }}
        }}
        return count;
      """

    with self.method("int", "any", {"target": self},
      brief="Test whether any bit is set",
      description="""
        Returns non-zero if at least one bit in the array is set.

        @param[in] target the bit array
        @return non-zero if any bit is set, zero otherwise
      """) as m:
      m.code = f"""
        size_t index;
        assert(target);
        for(index = 0; index < {self._word_count}; ++index) {{
          if(target->words[index]) return 1;
        }}
        return 0;
      """

    with self.method("int", "none", {"target": self},
      brief="Test whether no bits are set",
      description="""
        Returns non-zero if no bit in the array is set.

        @param[in] target the bit array
        @return non-zero if all bits are zero, zero otherwise
      """) as m:
      any_call = self.any(m.target)
      m.inline_code = f"""
        assert(target);
        return !{any_call};
      """

    with self.method(std.size_t, ("find", "first"), {"target": self},
      brief="Find the first set bit",
      description=f"""
        Returns the index of the lowest set bit, or {self._capacity} (the capacity)
        if no bit is set.

        @param[in] target the bit array
        @return index of the first set bit, or the capacity if none
      """) as m:
      m.code = f"""
        size_t index;
        unsigned char b;
        size_t bit;
        assert(target);
        for(index = 0; index < {self._word_count}; ++index) {{
          if(target->words[index]) {{
            b = target->words[index];
            bit = 0;
            while(!(b & 1)) {{ b >>= 1; ++bit; }}
            return index * 8 + bit;
          }}
        }}
        return {self._capacity};
      """

    # --- single-bit operations ---

    with self.method(None, "set", {"target": inout(self), "index": std.size_t},
      brief="Set the bit at the given index",
      description=f"""
        Sets bit `index` to 1. The index must be less than {self._capacity}.

        @param[in,out] target the bit array
        @param[in] index the position to set
      """) as m:
      m.inline_code = f"""
        assert(target);
        assert(index < {self._capacity});
        target->words[index >> 3] |= (unsigned char)(1 << (index & 7));
      """

    with self.method(None, "clear", {"target": inout(self), "index": std.size_t},
      brief="Clear the bit at the given index",
      description=f"""
        Sets bit `index` to 0. The index must be less than {self._capacity}.

        @param[in,out] target the bit array
        @param[in] index the position to clear
      """) as m:
      m.inline_code = f"""
        assert(target);
        assert(index < {self._capacity});
        target->words[index >> 3] &= (unsigned char)~(1 << (index & 7));
      """

    with self.method(None, "flip", {"target": inout(self), "index": std.size_t},
      brief="Toggle the bit at the given index",
      description=f"""
        Flips bit `index` (0 to 1, 1 to 0). The index must be less than {self._capacity}.

        @param[in,out] target the bit array
        @param[in] index the position to flip
      """) as m:
      m.inline_code = f"""
        assert(target);
        assert(index < {self._capacity});
        target->words[index >> 3] ^= (unsigned char)(1 << (index & 7));
      """

    with self.method("int", "test", {"target": self, "index": std.size_t},
      brief="Test the bit at the given index",
      description=f"""
        Returns 1 if bit `index` is set, 0 otherwise. The index must be less than {self._capacity}.

        @param[in] target the bit array
        @param[in] index the position to test
        @return 1 if the bit is set, 0 otherwise
      """) as m:
      m.inline_code = f"""
        assert(target);
        assert(index < {self._capacity});
        return (target->words[index >> 3] >> (index & 7)) & 1;
      """

    # --- bulk operations ---

    with self.method(None, ("set", "all"), {"target": inout(self)},
      brief="Set all bits to 1",
      description="""
        Sets every valid bit in the array to 1.

        @param[in,out] target the bit array
      """) as m:
      m.inline_code = f"""
        assert(target);
        memset(target->words, 0xFF, {self._word_count});
        target->words[{self._word_count - 1}] &= 0x{self._tail_mask:02x};
      """

    with self.method(None, ("flip", "all"), {"target": inout(self)},
      brief="Toggle all bits",
      description="""
        Flips every valid bit in the array.

        @param[in,out] target the bit array
      """) as m:
      m.code = f"""
        size_t index;
        assert(target);
        for(index = 0; index < {self._word_count}; ++index) target->words[index] = (unsigned char)~target->words[index];
        target->words[{self._word_count - 1}] &= 0x{self._tail_mask:02x};
      """

    # --- set algebra (in-place) ---

    with self.method(None, ("apply", "union"), {"target": inout(self), "source": self},
      constraint=lambda: self.algebraic_operations,
      optional_group="algebraic_operations",
      brief="In-place bitwise OR (union)",
      description="""
        Computes the union of two bit arrays: `target |= source`.

        @param[in,out] target the bit array to update
        @param[in] source the bit array to merge in
      """) as m:
      m.code = f"""
        size_t index;
        assert(target);
        assert(source);
        for(index = 0; index < {self._word_count}; ++index) target->words[index] |= source->words[index];
      """

    with self.method(None, ("apply", "intersection"), {"target": inout(self), "source": self},
      constraint=lambda: self.algebraic_operations,
      optional_group="algebraic_operations",
      brief="In-place bitwise AND (intersection)",
      description="""
        Computes the intersection of two bit arrays: `target &= source`.

        @param[in,out] target the bit array to update
        @param[in] source the bit array to intersect with
      """) as m:
      m.code = f"""
        size_t index;
        assert(target);
        assert(source);
        for(index = 0; index < {self._word_count}; ++index) target->words[index] &= source->words[index];
      """

    with self.method(None, ("apply", "difference"), {"target": inout(self), "source": self},
      constraint=lambda: self.algebraic_operations,
      optional_group="algebraic_operations",
      brief="In-place bitwise AND NOT (difference)",
      description="""
        Computes the difference of two bit arrays: `target &= ~source`.

        @param[in,out] target the bit array to update
        @param[in] source the bit array to subtract
      """) as m:
      m.code = f"""
        size_t index;
        assert(target);
        assert(source);
        for(index = 0; index < {self._word_count}; ++index) target->words[index] &= (unsigned char)~source->words[index];
      """

    with self.method(None, ("apply", "symmetric", "difference"), {"target": inout(self), "source": self},
      constraint=lambda: self.algebraic_operations,
      optional_group="algebraic_operations",
      brief="In-place bitwise XOR (symmetric difference)",
      description="""
        Computes the symmetric difference of two bit arrays: `target ^= source`.

        @param[in,out] target the bit array to update
        @param[in] source the bit array to XOR with
      """) as m:
      m.code = f"""
        size_t index;
        assert(target);
        assert(source);
        for(index = 0; index < {self._word_count}; ++index) target->words[index] ^= source->words[index];
      """

    # --- constructing algebraic operations ---

    with self.method(None, ("create", "union"), {"target": out(self), "left": self, "right": self},
      constraint=lambda: self.algebraic_operations,
      optional_group="algebraic_operations",
      brief="Construct bitwise OR (union) of two bit arrays",
      description="""
        Constructs target as the union of two bit arrays: `target = left | right`.

        @param[out] target the uninitialized bit array to construct
        @param[in] left the first bit array
        @param[in] right the second bit array
      """) as m:
      m.code = f"""
        size_t index;
        assert(target);
        assert(left);
        assert(right);
        for(index = 0; index < {self._word_count}; ++index) target->words[index] = left->words[index] | right->words[index];
      """

    with self.method(None, ("create", "intersection"), {"target": out(self), "left": self, "right": self},
      constraint=lambda: self.algebraic_operations,
      optional_group="algebraic_operations",
      brief="Construct bitwise AND (intersection) of two bit arrays",
      description="""
        Constructs target as the intersection of two bit arrays: `target = left & right`.

        @param[out] target the uninitialized bit array to construct
        @param[in] left the first bit array
        @param[in] right the second bit array
      """) as m:
      m.code = f"""
        size_t index;
        assert(target);
        assert(left);
        assert(right);
        for(index = 0; index < {self._word_count}; ++index) target->words[index] = left->words[index] & right->words[index];
      """

    with self.method(None, ("create", "difference"), {"target": out(self), "left": self, "right": self},
      constraint=lambda: self.algebraic_operations,
      optional_group="algebraic_operations",
      brief="Construct bitwise AND NOT (difference) of two bit arrays",
      description="""
        Constructs target as the difference of two bit arrays: `target = left & ~right`.

        @param[out] target the uninitialized bit array to construct
        @param[in] left the first bit array
        @param[in] right the bit array to subtract
      """) as m:
      m.code = f"""
        size_t index;
        assert(target);
        assert(left);
        assert(right);
        for(index = 0; index < {self._word_count}; ++index) target->words[index] = left->words[index] & (unsigned char)~right->words[index];
      """

    with self.method(None, ("create", "symmetric", "difference"), {"target": out(self), "left": self, "right": self},
      constraint=lambda: self.algebraic_operations,
      optional_group="algebraic_operations",
      brief="Construct bitwise XOR (symmetric difference) of two bit arrays",
      description="""
        Constructs target as the symmetric difference of two bit arrays: `target = left ^ right`.

        @param[out] target the uninitialized bit array to construct
        @param[in] left the first bit array
        @param[in] right the second bit array
      """) as m:
      m.code = f"""
        size_t index;
        assert(target);
        assert(left);
        assert(right);
        for(index = 0; index < {self._word_count}; ++index) target->words[index] = left->words[index] ^ right->words[index];
      """

    # --- predicates ---

    with self.method("int", ("is", "subset"), {"left": self, "right": self},
      constraint=lambda: self.algebraic_operations,
      optional_group="algebraic_operations",
      brief="Test whether left is a subset of right",
      description="""
        Returns non-zero if every bit set in `left` is also set in `right`.

        @param[in] left the candidate subset
        @param[in] right the candidate superset
        @return non-zero if left is a subset of right, zero otherwise
      """) as m:
      m.code = f"""
        size_t index;
        assert(left);
        assert(right);
        for(index = 0; index < {self._word_count}; ++index) {{
          if(left->words[index] & (unsigned char)~right->words[index]) return 0;
        }}
        return 1;
      """

  def _render_struct(self, stream, header):
    super()._render_struct(stream, header)
    stream.append(f"""
      struct {self.name} {{
        unsigned char words[{self._word_count}]; /**< @private */
      }};
    """)
