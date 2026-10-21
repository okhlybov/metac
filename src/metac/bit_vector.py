import metac.std as std
from metac.hash import XorRot
from metac.memory import Manager
from metac.core import inout, out, Composite, _StructRenderer


# Dynamically resizable packed bit vector container
class Vector(_StructRenderer, Composite):

  brief = "Dynamically resizable packed bit vector container"

  def __init__(self, name, *args, algebraic_operations=True, memory=Manager(), hasher=XorRot(), dependencies=(), **kwargs):
    self.algebraic_operations = bool(algebraic_operations)
    self.memory = memory
    self.hasher = hasher
    super().__init__(name, *args, dependencies=(*dependencies, std.assert_h, std.string_h, std.stdlib_h, memory, hasher), **kwargs)

  @property
  def constructible(self):
    return True

  @property
  def default_constructible(self):
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
  def comparable(self):
    return True

  @property
  def orderable(self):
    return False

  @property
  def hashable(self):
    return True

  @property
  def zero_initializable(self):
    return True

  def __setup__(self):
    super().__setup__()

    self.description = """
      Dynamically resizable bit vector storing packed bits on the heap with word-level parallel operations.

      Bits are stored densely as `size_t` words (64 bits per word on 64-bit platforms).
      Supports dynamic resizing, amortized O(1) push and pop, bitwise inspection, and set algebra operations.
    """

    # --- value protocol ---

    with self.create as m:
      m.inline_code = f"""
        assert(target);
        target->words = NULL;
        target->size = 0;
        target->capacity = 0;
      """

    with self.destroy as m:
      m.inline_code = f"""
        assert(target);
        if(target->words) {{
          {self.memory.free("target->words")};
        }}
      """

    with self.copy as m:
      m.code = f"""
        size_t word_count;
        assert(target);
        assert(source);
        target->size = source->size;
        word_count = (source->size + sizeof(size_t) * 8 - 1) / (sizeof(size_t) * 8);
        target->capacity = word_count > 0 ? word_count : (source->capacity > 0 ? 1 : 0);
        if(target->capacity > 0) {{
          target->words = (size_t*){self.memory.allocate("target->capacity * sizeof(size_t)")};
          assert(target->words);
          if(word_count > 0) {{
            memcpy(target->words, source->words, word_count * sizeof(size_t));
          }}
          if(target->capacity > word_count) {{
            memset(target->words + word_count, 0, (target->capacity - word_count) * sizeof(size_t));
          }}
        }} else {{
          target->words = NULL;
        }}
      """

    with self.move as m:
      m.inline_code = f"""
        assert(target);
        assert(source);
        target->words = source->words;
        target->size = source->size;
        target->capacity = source->capacity;
        source->words = NULL;
        source->size = 0;
        source->capacity = 0;
      """

    with self.swap as m:
      m.inline_code = f"""
        size_t* temp_words;
        size_t temp_val;
        assert(left);
        assert(right);
        temp_words = left->words; left->words = right->words; right->words = temp_words;
        temp_val = left->size; left->size = right->size; right->size = temp_val;
        temp_val = left->capacity; left->capacity = right->capacity; right->capacity = temp_val;
      """

    with self.equal as m:
      m.code = f"""
        size_t full_words, remainder, word_bits;
        assert(left);
        assert(right);
        if(left->size != right->size) return 0;
        if(left->size == 0) return 1;
        word_bits = sizeof(size_t) * 8;
        full_words = left->size / word_bits;
        remainder = left->size % word_bits;
        if(full_words > 0 && memcmp(left->words, right->words, full_words * sizeof(size_t)) != 0) return 0;
        if(remainder > 0) {{
          size_t mask = (((size_t)1) << remainder) - 1;
          if((left->words[full_words] & mask) != (right->words[full_words] & mask)) return 0;
        }}
        return 1;
      """

    with self.hash as m:
      def _hash(m):
        state = self.hasher.state_t.variable("state")
        return f"""
          size_t result, index, full_words, remainder, word_bits;
          {state.definition};
          assert(target);
          if(target->size == 0) return 0;
          word_bits = sizeof(size_t) * 8;
          full_words = target->size / word_bits;
          remainder = target->size % word_bits;
          {self.hasher.create(state)};
          for(index = 0; index < full_words; ++index) {{
            {self.hasher.update(state, "target->words[index]")};
          }}
          if(remainder > 0) {{
            size_t masked = target->words[full_words] & ((((size_t)1) << remainder) - 1);
            {self.hasher.update(state, "masked")};
          }}
          result = {self.hasher.hash(state)};
          {self.hasher.destroy(state)};
          return result;
        """
      m.code = _hash

    # --- construction with size ---

    with self.method(None, ("create", "size"), {"target": inout(self), "size": std.size_t},
      brief="Create bit vector with specified bit count (all zero)",
      description="""
        Allocates and initializes a bit vector of `size` bits, all set to zero.

        @param[out] target the bit vector to construct
        @param[in] size the initial number of bits
      """) as m:
      m.code = f"""
        size_t word_count;
        assert(target);
        target->size = size;
        word_count = (size + sizeof(size_t) * 8 - 1) / (sizeof(size_t) * 8);
        target->capacity = word_count > 0 ? word_count : 1;
        target->words = (size_t*){self.memory.allocate("target->capacity * sizeof(size_t)")};
        assert(target->words);
        memset(target->words, 0, target->capacity * sizeof(size_t));
      """

    # --- queries ---

    with self.method(std.size_t, "size", {"target": self},
      brief="Get the number of bits in the vector",
      description="""
        Returns the current number of bits in the bit vector.

        @param[in] target the bit vector
        @return the number of bits
      """) as m:
      m.inline_code = f"""
        assert(target);
        return target->size;
      """

    with self.method(std.size_t, "capacity", {"target": self},
      brief="Get the total bit capacity before reallocation",
      description="""
        Returns the total number of bits the vector can hold without reallocating.

        @param[in] target the bit vector
        @return the capacity in bits
      """) as m:
      m.inline_code = f"""
        assert(target);
        return target->capacity * sizeof(size_t) * 8;
      """

    with self.method("int", "empty", {"target": self},
      brief="Test whether the bit vector is empty",
      description="""
        Returns non-zero if the vector holds zero bits.

        @param[in] target the bit vector
        @return non-zero if empty, zero otherwise
      """) as m:
      m.inline_code = f"""
        assert(target);
        return target->size == 0;
      """

    with self.method(None, "reserve", {"target": inout(self), "capacity": std.size_t},
      brief="Reserve storage for at least the specified number of bits",
      description="""
        Ensures the vector has storage allocated for at least `capacity` bits.

        @param[in,out] target the bit vector
        @param[in] capacity the minimum bit capacity to reserve
      """) as m:
      m.code = f"""
        size_t needed_words;
        assert(target);
        needed_words = (capacity + sizeof(size_t) * 8 - 1) / (sizeof(size_t) * 8);
        if(needed_words > target->capacity) {{
          size_t* new_words = (size_t*){self.memory.allocate("needed_words * sizeof(size_t)")};
          assert(new_words);
          if(target->words && target->capacity > 0) {{
            memcpy(new_words, target->words, target->capacity * sizeof(size_t));
            {self.memory.free("target->words")};
          }}
          memset(new_words + target->capacity, 0, (needed_words - target->capacity) * sizeof(size_t));
          target->words = new_words;
          target->capacity = needed_words;
        }}
      """

    with self.method(None, "compact", {"target": inout(self)},
      brief="Compact capacity to match current size",
      description="""
        Releases unused capacity, reducing memory allocation to the minimum needed for `size` bits.

        @param[in,out] target the bit vector
      """) as m:
      m.code = f"""
        size_t needed_words;
        assert(target);
        needed_words = (target->size + sizeof(size_t) * 8 - 1) / (sizeof(size_t) * 8);
        if(needed_words == 0) {{
          if(target->words) {{
            {self.memory.free("target->words")};
            target->words = NULL;
          }}
          target->capacity = 0;
        }} else if(needed_words < target->capacity) {{
          size_t* new_words = (size_t*){self.memory.allocate("needed_words * sizeof(size_t)")};
          assert(new_words);
          memcpy(new_words, target->words, needed_words * sizeof(size_t));
          {self.memory.free("target->words")};
          target->words = new_words;
          target->capacity = needed_words;
        }}
      """

    with self.method(None, "clear", {"target": inout(self)},
      brief="Clear all bits leaving capacity intact",
      description="""
        Resets the bit count to zero while preserving the allocated memory buffer.

        @param[in,out] target the bit vector
      """) as m:
      m.code = f"""
        assert(target);
        if(target->size > 0 && target->words) {{
          size_t active_words = (target->size + sizeof(size_t) * 8 - 1) / (sizeof(size_t) * 8);
          memset(target->words, 0, active_words * sizeof(size_t));
        }}
        target->size = 0;
      """

    with self.method(None, "resize", {"target": inout(self), "new_size": std.size_t},
      brief="Resize the bit vector to the specified number of bits",
      description="""
        Grows or shrinks the vector. New bits are initialized to 0.

        @param[in,out] target the bit vector
        @param[in] new_size the new number of bits
      """) as m:
      m.code = f"""
        size_t word_bits = sizeof(size_t) * 8;
        size_t needed_words;
        assert(target);
        if(new_size > target->size) {{
          needed_words = (new_size + word_bits - 1) / word_bits;
          if(needed_words > target->capacity) {{
            size_t new_cap = target->capacity > 0 ? target->capacity * 2 : 2;
            if(new_cap < needed_words) new_cap = needed_words;
            {self.reserve(m.target, "new_cap * word_bits")};
          }}
        }} else if(new_size < target->size) {{
          size_t rem = new_size % word_bits;
          size_t last_word = new_size / word_bits;
          if(rem > 0 && target->words) {{
            target->words[last_word] &= (((size_t)1) << rem) - 1;
          }}
          if(target->words) {{
            size_t cur_words = (target->size + word_bits - 1) / word_bits;
            size_t new_words = (new_size + word_bits - 1) / word_bits;
            if(cur_words > new_words) {{
              memset(target->words + new_words, 0, (cur_words - new_words) * sizeof(size_t));
            }}
          }}
        }}
        target->size = new_size;
      """

    # --- bit modifications ---

    with self.method(None, "push", {"target": inout(self), "bit": "int"},
      brief="Append a bit to the end of the vector",
      description="""
        Appends a bit to the end of the vector, growing capacity if needed.

        @param[in,out] target the bit vector
        @param[in] bit the bit value to append (0 or non-zero)
      """) as m:
      m.code = f"""
        size_t word_bits = sizeof(size_t) * 8;
        size_t needed_words;
        assert(target);
        needed_words = (target->size + 1 + word_bits - 1) / word_bits;
        if(needed_words > target->capacity) {{
          size_t new_cap = target->capacity > 0 ? target->capacity * 2 : 2;
          if(new_cap < needed_words) new_cap = needed_words;
          {self.reserve(m.target, "new_cap * word_bits")};
        }}
        if(bit) {{
          target->words[target->size / word_bits] |= (((size_t)1) << (target->size % word_bits));
        }} else {{
          target->words[target->size / word_bits] &= ~(((size_t)1) << (target->size % word_bits));
        }}
        ++target->size;
      """

    with self.method("int", "pop", {"target": inout(self)},
      brief="Remove and return the last bit",
      description="""
        Removes the last bit from the vector and returns its value.

        @param[in,out] target the bit vector
        @return the removed bit value (0 or 1)
      """) as m:
      m.code = f"""
        size_t word_bits = sizeof(size_t) * 8;
        int bit;
        assert(target);
        assert(target->size > 0);
        --target->size;
        bit = (int)((target->words[target->size / word_bits] >> (target->size % word_bits)) & 1);
        target->words[target->size / word_bits] &= ~(((size_t)1) << (target->size % word_bits));
        return bit;
      """

    with self.method("int", "get", {"target": self, "index": std.size_t},
      brief="Get the bit at the given index",
      description="""
        Returns 1 if bit `index` is set, 0 otherwise.

        @param[in] target the bit vector
        @param[in] index the bit index (must be < size)
        @return 1 if set, 0 otherwise
      """) as m:
      m.inline_code = f"""
        assert(target);
        assert(index < target->size);
        return (int)((target->words[index / (sizeof(size_t) * 8)] >> (index % (sizeof(size_t) * 8))) & 1);
      """

    with self.method("int", "test", {"target": self, "index": std.size_t},
      brief="Test whether the bit at the given index is set",
      description="""
        Returns 1 if bit `index` is set, 0 otherwise.

        @param[in] target the bit vector
        @param[in] index the bit index (must be < size)
        @return 1 if set, 0 otherwise
      """) as m:
      get_call = self.get(m.target, m.index)
      m.inline_code = f"""
        return {get_call};
      """

    with self.method(None, "set", {"target": inout(self), "index": std.size_t, "bit": "int"},
      brief="Set the bit at the given index",
      description="""
        Sets bit `index` to 1 if `bit` is non-zero, or to 0 if `bit` is zero.

        @param[in,out] target the bit vector
        @param[in] index the bit index (must be < size)
        @param[in] bit the bit value (0 or non-zero)
      """) as m:
      m.inline_code = f"""
        size_t word_bits = sizeof(size_t) * 8;
        assert(target);
        assert(index < target->size);
        if(bit) {{
          target->words[index / word_bits] |= (((size_t)1) << (index % word_bits));
        }} else {{
          target->words[index / word_bits] &= ~(((size_t)1) << (index % word_bits));
        }}
      """

    with self.method(None, ("clear", "bit"), {"target": inout(self), "index": std.size_t},
      brief="Clear the bit at the given index to 0",
      description="""
        Sets bit `index` to 0.

        @param[in,out] target the bit vector
        @param[in] index the bit index (must be < size)
      """) as m:
      m.inline_code = f"""
        assert(target);
        assert(index < target->size);
        target->words[index / (sizeof(size_t) * 8)] &= ~(((size_t)1) << (index % (sizeof(size_t) * 8)));
      """

    with self.method(None, ("flip", "bit"), {"target": inout(self), "index": std.size_t},
      brief="Toggle the bit at the given index",
      description="""
        Toggles bit `index` (0 to 1, 1 to 0).

        @param[in,out] target the bit vector
        @param[in] index the bit index (must be < size)
      """) as m:
      m.inline_code = f"""
        assert(target);
        assert(index < target->size);
        target->words[index / (sizeof(size_t) * 8)] ^= (((size_t)1) << (index % (sizeof(size_t) * 8)));
      """

    with self.method(None, ("set", "all"), {"target": inout(self)},
      brief="Set all bits to 1",
      description="""
        Sets every bit in the vector to 1.

        @param[in,out] target the bit vector
      """) as m:
      m.code = f"""
        size_t word_bits = sizeof(size_t) * 8;
        size_t full_words, rem;
        assert(target);
        if(target->size == 0) return;
        full_words = target->size / word_bits;
        rem = target->size % word_bits;
        if(full_words > 0) {{
          memset(target->words, 0xFF, full_words * sizeof(size_t));
        }}
        if(rem > 0) {{
          target->words[full_words] = (((size_t)1) << rem) - 1;
        }}
      """

    with self.method(None, ("reset", "all"), {"target": inout(self)},
      brief="Reset all bits to 0",
      description="""
        Sets every bit in the vector to 0.

        @param[in,out] target the bit vector
      """) as m:
      m.code = f"""
        size_t active_words;
        assert(target);
        if(target->size == 0) return;
        active_words = (target->size + sizeof(size_t) * 8 - 1) / (sizeof(size_t) * 8);
        memset(target->words, 0, active_words * sizeof(size_t));
      """

    with self.method(None, "flip", {"target": inout(self)},
      brief="Invert all bits",
      description="""
        Toggles every bit in the vector (0 becomes 1, 1 becomes 0).

        @param[in,out] target the bit vector
      """) as m:
      m.code = f"""
        size_t word_bits = sizeof(size_t) * 8;
        size_t full_words, rem, index;
        assert(target);
        if(target->size == 0) return;
        full_words = target->size / word_bits;
        rem = target->size % word_bits;
        for(index = 0; index < full_words; ++index) {{
          target->words[index] = ~target->words[index];
        }}
        if(rem > 0) {{
          size_t mask = (((size_t)1) << rem) - 1;
          target->words[full_words] = (~target->words[full_words]) & mask;
        }}
      """

    # --- queries and counts ---

    with self.method(std.size_t, "count", {"target": self},
      brief="Count the number of set bits (population count)",
      description="""
        Counts the number of bits in the vector that are set to 1.

        @param[in] target the bit vector
        @return the number of set bits
      """) as m:
      m.code = f"""
        size_t word_bits = sizeof(size_t) * 8;
        size_t full_words, rem, index, total = 0;
        size_t w;
        assert(target);
        if(target->size == 0) return 0;
        full_words = target->size / word_bits;
        rem = target->size % word_bits;
        for(index = 0; index < full_words; ++index) {{
          w = target->words[index];
          while(w) {{ w &= w - 1; ++total; }}
        }}
        if(rem > 0) {{
          w = target->words[full_words] & ((((size_t)1) << rem) - 1);
          while(w) {{ w &= w - 1; ++total; }}
        }}
        return total;
      """

    with self.method("int", "any", {"target": self},
      brief="Test whether any bit is set",
      description="""
        Returns non-zero if at least one bit in the vector is set.

        @param[in] target the bit vector
        @return non-zero if any bit is set, zero otherwise
      """) as m:
      m.code = f"""
        size_t word_bits = sizeof(size_t) * 8;
        size_t full_words, rem, index;
        assert(target);
        if(target->size == 0) return 0;
        full_words = target->size / word_bits;
        rem = target->size % word_bits;
        for(index = 0; index < full_words; ++index) {{
          if(target->words[index] != 0) return 1;
        }}
        if(rem > 0) {{
          if((target->words[full_words] & ((((size_t)1) << rem) - 1)) != 0) return 1;
        }}
        return 0;
      """

    with self.method("int", "all", {"target": self},
      brief="Test whether all bits are set",
      description="""
        Returns non-zero if every bit in the vector is set to 1.

        @param[in] target the bit vector
        @return non-zero if all bits are set, zero otherwise
      """) as m:
      m.code = f"""
        size_t word_bits = sizeof(size_t) * 8;
        size_t full_words, rem, index;
        assert(target);
        if(target->size == 0) return 1;
        full_words = target->size / word_bits;
        rem = target->size % word_bits;
        for(index = 0; index < full_words; ++index) {{
          if(target->words[index] != ~(size_t)0) return 0;
        }}
        if(rem > 0) {{
          size_t mask = (((size_t)1) << rem) - 1;
          if((target->words[full_words] & mask) != mask) return 0;
        }}
        return 1;
      """

    with self.method("int", "none", {"target": self},
      brief="Test whether no bits are set",
      description="""
        Returns non-zero if no bits in the vector are set.

        @param[in] target the bit vector
        @return non-zero if all bits are zero, zero otherwise
      """) as m:
      any_call = self.any(m.target)
      m.inline_code = f"""
        assert(target);
        return !{any_call};
      """

    with self.method(std.size_t, ("find", "first"), {"target": self},
      brief="Find the index of the first set bit",
      description="""
        Returns the index of the lowest set bit, or `size` if no bit is set.

        @param[in] target the bit vector
        @return index of the first set bit, or size if none
      """) as m:
      m.code = f"""
        size_t word_bits = sizeof(size_t) * 8;
        size_t full_words, rem, index, bit;
        size_t w;
        assert(target);
        if(target->size == 0) return 0;
        full_words = target->size / word_bits;
        rem = target->size % word_bits;
        for(index = 0; index < full_words; ++index) {{
          if(target->words[index]) {{
            w = target->words[index];
            bit = 0;
            while(!(w & 1)) {{ w >>= 1; ++bit; }}
            return index * word_bits + bit;
          }}
        }}
        if(rem > 0) {{
          w = target->words[full_words] & ((((size_t)1) << rem) - 1);
          if(w) {{
            bit = 0;
            while(!(w & 1)) {{ w >>= 1; ++bit; }}
            return full_words * word_bits + bit;
          }}
        }}
        return target->size;
      """

    # --- set algebra (in-place) ---

    with self.method(None, ("apply", "union"), {"target": inout(self), "source": self},
      constraint=lambda: self.algebraic_operations,
      optional_group="algebraic_operations",
      brief="In-place bitwise OR (union)",
      description="""
        Computes the union of two bit vectors: `target |= source`.
        If source is longer, target is resized to match source.

        @param[in,out] target the bit vector to update
        @param[in] source the bit vector to merge in
      """) as m:
      m.code = f"""
        size_t word_bits = sizeof(size_t) * 8;
        size_t common_words, index;
        assert(target);
        assert(source);
        if(source->size > target->size) {{
          {self.resize(m.target, "source->size")};
        }}
        common_words = (source->size + word_bits - 1) / word_bits;
        for(index = 0; index < common_words; ++index) {{
          target->words[index] |= source->words[index];
        }}
        if(target->size % word_bits != 0) {{
          target->words[target->size / word_bits] &= (((size_t)1) << (target->size % word_bits)) - 1;
        }}
      """

    with self.method(None, ("apply", "intersection"), {"target": inout(self), "source": self},
      constraint=lambda: self.algebraic_operations,
      optional_group="algebraic_operations",
      brief="In-place bitwise AND (intersection)",
      description="""
        Computes the intersection of two bit vectors: `target &= source`.
        Any bits beyond source's length are cleared to 0.

        @param[in,out] target the bit vector to update
        @param[in] source the bit vector to intersect with
      """) as m:
      m.code = f"""
        size_t word_bits = sizeof(size_t) * 8;
        size_t common_words, target_words, index;
        assert(target);
        assert(source);
        common_words = (source->size + word_bits - 1) / word_bits;
        target_words = (target->size + word_bits - 1) / word_bits;
        if(common_words > target_words) common_words = target_words;
        for(index = 0; index < common_words; ++index) {{
          target->words[index] &= source->words[index];
        }}
        for(index = common_words; index < target_words; ++index) {{
          target->words[index] = 0;
        }}
        if(target->size % word_bits != 0) {{
          target->words[target->size / word_bits] &= (((size_t)1) << (target->size % word_bits)) - 1;
        }}
      """

    with self.method(None, ("apply", "difference"), {"target": inout(self), "source": self},
      constraint=lambda: self.algebraic_operations,
      optional_group="algebraic_operations",
      brief="In-place bitwise AND NOT (difference)",
      description="""
        Computes the difference of two bit vectors: `target &= ~source`.

        @param[in,out] target the bit vector to update
        @param[in] source the bit vector to subtract
      """) as m:
      m.code = f"""
        size_t word_bits = sizeof(size_t) * 8;
        size_t common_words, target_words, index;
        assert(target);
        assert(source);
        common_words = (source->size + word_bits - 1) / word_bits;
        target_words = (target->size + word_bits - 1) / word_bits;
        if(common_words > target_words) common_words = target_words;
        for(index = 0; index < common_words; ++index) {{
          target->words[index] &= ~source->words[index];
        }}
        if(target->size % word_bits != 0) {{
          target->words[target->size / word_bits] &= (((size_t)1) << (target->size % word_bits)) - 1;
        }}
      """

    with self.method(None, ("apply", "symmetric", "difference"), {"target": inout(self), "source": self},
      constraint=lambda: self.algebraic_operations,
      optional_group="algebraic_operations",
      brief="In-place bitwise XOR (symmetric difference)",
      description="""
        Computes the symmetric difference of two bit vectors: `target ^= source`.

        @param[in,out] target the bit vector to update
        @param[in] source the bit vector to XOR with
      """) as m:
      m.code = f"""
        size_t word_bits = sizeof(size_t) * 8;
        size_t common_words, index;
        assert(target);
        assert(source);
        if(source->size > target->size) {{
          {self.resize(m.target, "source->size")};
        }}
        common_words = (source->size + word_bits - 1) / word_bits;
        for(index = 0; index < common_words; ++index) {{
          target->words[index] ^= source->words[index];
        }}
        if(target->size % word_bits != 0) {{
          target->words[target->size / word_bits] &= (((size_t)1) << (target->size % word_bits)) - 1;
        }}
      """

    # --- constructing algebraic operations ---

    with self.method(None, ("create", "union"), {"target": out(self), "left": self, "right": self},
      constraint=lambda: self.algebraic_operations,
      optional_group="algebraic_operations",
      brief="Construct bitwise OR (union) of two bit vectors",
      description="""
        Constructs target as the union of two bit vectors: `target = left | right`.
        Target size is max(left->size, right->size).

        @param[out] target the uninitialized bit vector to construct
        @param[in] left the first bit vector
        @param[in] right the second bit vector
      """) as m:
      m.code = f"""
        size_t word_bits = sizeof(size_t) * 8;
        size_t max_size, left_words, right_words, common_words, index;
        assert(target);
        assert(left);
        assert(right);
        max_size = left->size >= right->size ? left->size : right->size;
        {self.create_size(m.target, "max_size")};
        left_words = (left->size + word_bits - 1) / word_bits;
        right_words = (right->size + word_bits - 1) / word_bits;
        common_words = left_words <= right_words ? left_words : right_words;
        for(index = 0; index < common_words; ++index) {{
          target->words[index] = left->words[index] | right->words[index];
        }}
        for(index = common_words; index < left_words; ++index) {{
          target->words[index] = left->words[index];
        }}
        for(index = common_words; index < right_words; ++index) {{
          target->words[index] = right->words[index];
        }}
        if(target->size % word_bits != 0) {{
          target->words[target->size / word_bits] &= (((size_t)1) << (target->size % word_bits)) - 1;
        }}
      """

    with self.method(None, ("create", "intersection"), {"target": out(self), "left": self, "right": self},
      constraint=lambda: self.algebraic_operations,
      optional_group="algebraic_operations",
      brief="Construct bitwise AND (intersection) of two bit vectors",
      description="""
        Constructs target as the intersection of two bit vectors: `target = left & right`.
        Target size is min(left->size, right->size).

        @param[out] target the uninitialized bit vector to construct
        @param[in] left the first bit vector
        @param[in] right the second bit vector
      """) as m:
      m.code = f"""
        size_t word_bits = sizeof(size_t) * 8;
        size_t min_size, target_words, index;
        assert(target);
        assert(left);
        assert(right);
        min_size = left->size <= right->size ? left->size : right->size;
        {self.create_size(m.target, "min_size")};
        target_words = (target->size + word_bits - 1) / word_bits;
        for(index = 0; index < target_words; ++index) {{
          target->words[index] = left->words[index] & right->words[index];
        }}
        if(target->size % word_bits != 0) {{
          target->words[target->size / word_bits] &= (((size_t)1) << (target->size % word_bits)) - 1;
        }}
      """

    with self.method(None, ("create", "difference"), {"target": out(self), "left": self, "right": self},
      constraint=lambda: self.algebraic_operations,
      optional_group="algebraic_operations",
      brief="Construct bitwise AND NOT (difference) of two bit vectors",
      description="""
        Constructs target as the difference of two bit vectors: `target = left & ~right`.
        Target size is left->size.

        @param[out] target the uninitialized bit vector to construct
        @param[in] left the first bit vector
        @param[in] right the bit vector to subtract
      """) as m:
      m.code = f"""
        size_t word_bits = sizeof(size_t) * 8;
        size_t left_words, right_words, common_words, index;
        assert(target);
        assert(left);
        assert(right);
        {self.create_size(m.target, "left->size")};
        left_words = (left->size + word_bits - 1) / word_bits;
        right_words = (right->size + word_bits - 1) / word_bits;
        common_words = left_words <= right_words ? left_words : right_words;
        for(index = 0; index < common_words; ++index) {{
          target->words[index] = left->words[index] & ~right->words[index];
        }}
        for(index = common_words; index < left_words; ++index) {{
          target->words[index] = left->words[index];
        }}
        if(target->size % word_bits != 0) {{
          target->words[target->size / word_bits] &= (((size_t)1) << (target->size % word_bits)) - 1;
        }}
      """

    with self.method(None, ("create", "symmetric", "difference"), {"target": out(self), "left": self, "right": self},
      constraint=lambda: self.algebraic_operations,
      optional_group="algebraic_operations",
      brief="Construct bitwise XOR (symmetric difference) of two bit vectors",
      description="""
        Constructs target as the symmetric difference of two bit vectors: `target = left ^ right`.
        Target size is max(left->size, right->size).

        @param[out] target the uninitialized bit vector to construct
        @param[in] left the first bit vector
        @param[in] right the second bit vector
      """) as m:
      m.code = f"""
        size_t word_bits = sizeof(size_t) * 8;
        size_t max_size, left_words, right_words, common_words, index;
        assert(target);
        assert(left);
        assert(right);
        max_size = left->size >= right->size ? left->size : right->size;
        {self.create_size(m.target, "max_size")};
        left_words = (left->size + word_bits - 1) / word_bits;
        right_words = (right->size + word_bits - 1) / word_bits;
        common_words = left_words <= right_words ? left_words : right_words;
        for(index = 0; index < common_words; ++index) {{
          target->words[index] = left->words[index] ^ right->words[index];
        }}
        for(index = common_words; index < left_words; ++index) {{
          target->words[index] = left->words[index];
        }}
        for(index = common_words; index < right_words; ++index) {{
          target->words[index] = right->words[index];
        }}
        if(target->size % word_bits != 0) {{
          target->words[target->size / word_bits] &= (((size_t)1) << (target->size % word_bits)) - 1;
        }}
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
        size_t word_bits = sizeof(size_t) * 8;
        size_t common_words, left_words, right_words, index;
        assert(left);
        assert(right);
        left_words = (left->size + word_bits - 1) / word_bits;
        right_words = (right->size + word_bits - 1) / word_bits;
        common_words = left_words < right_words ? left_words : right_words;
        for(index = 0; index < common_words; ++index) {{
          if(left->words[index] & ~right->words[index]) return 0;
        }}
        for(index = common_words; index < left_words; ++index) {{
          if(left->words[index] != 0) return 0;
        }}
        return 1;
      """

  def _render_struct(self, stream, header):
    super()._render_struct(stream, header)
    stream.append(f"""
      struct {self.name} {{
        size_t* words; /**< @private */
        size_t size; /**< @private */
        size_t capacity; /**< @private */
      }};
    """)
