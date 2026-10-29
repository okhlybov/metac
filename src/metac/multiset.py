import metac.std as std
from metac.core import inout, out, Callable, enforced, Comparable, Coerce
from metac.traversable import Traversable
from metac.insertable import Insertable


# Abstract base for all multiset collections
class Multiset(Traversable, Insertable):

  @enforced
  def __init__(self, name: str, element: Coerce[Comparable], *args, algebraic_operations=True, **kwargs):
    self.algebraic_operations = bool(algebraic_operations)
    super().__init__(name, element, *args, **kwargs)

  def __setup__(self):
    super().__setup__()

    self.method("int", "put", {"target": inout(self), "element": self.element}, constraint=lambda: self.element.copyable and self.element.comparable, brief="Insert element into multiset",
      description="""
        Inserts the element into the multiset, preserving any existing duplicates.
        Every multiset implementation inherits this protocol operation.

        @param[in,out] target the multiset to insert into
        @param[in] element the element to insert
        @return always non-zero
      """)

    self.method("int", "emplace", {"target": inout(self)} | self.element.constructor_parameters,
      constraint=lambda: self.element.emplaceable and self.element.comparable,
      brief="Construct element in-place",
      description="""
        Constructs an element in-place with forwarded parameters and inserts it into the
        multiset, preserving any existing duplicates.
        Every multiset implementation inherits this protocol operation.
        Returns non-zero indicating the element was inserted.

        @param[in,out] target the multiset to insert into
        @return non-zero once the constructed element was inserted
      """)

    self.method("int", "remove", {"target": inout(self), "element": self.element}, constraint=lambda: self.element.comparable, brief="Remove one occurrence of element",
      description="""
        Removes one occurrence of the element if present, leaving the multiset unchanged otherwise.
        Every multiset implementation inherits this protocol operation.

        @param[in,out] target the multiset to remove from
        @param[in] element the element to remove
        @return non-zero if an element was removed and zero if the multiset held no equal element
      """)

    self.method(std.size_t, "wipe", {"target": inout(self), "element": self.element}, constraint=lambda: self.element.comparable, brief="Remove all occurrences of element",
      description="""
        Removes all occurrences of the element from the multiset.
        Every multiset implementation inherits this protocol operation.

        @param[in,out] target the multiset to remove from
        @param[in] element the element to remove
        @return the number of occurrences removed
      """)

    self.method(std.size_t, "count", {"target": self, "element": self.element}, constraint=lambda: self.element.comparable, brief="Count occurrences of element",
      description="""
        Returns the multiplicity (number of occurrences) of the element in the multiset.
        Every multiset implementation inherits this protocol operation.

        @param[in] target the multiset to query
        @param[in] element the element to count
        @return number of occurrences
      """)

    self.method(Callable.Parameter(self.range), ("equal", "range"), {"target": self, "element": self.element}, constraint=lambda: self.element.comparable, brief="Get range covering all occurrences of element",
      description="""
        Returns the range covering all occurrences of the element in the multiset.
        If the element is absent, an empty range is returned.

        @param[in] target the multiset to search
        @param[in] element the element to search for
        @return the range spanning all matching occurrences
      """)

    range = self.range
    r = range.variable("r")
    temp = self.variable("temp")
    algebra_constraint = lambda: self.algebraic_operations and self.element.copyable and self.element.comparable
    subset_constraint = lambda: self.algebraic_operations and self.element.comparable

    with self.method(std.size_t, ("apply", "union"), {"target": inout(self), "other": self}, constraint=algebra_constraint, optional_group="algebraic_operations", brief="Multiset union (maximum multiplicities)",
      description="""
        Expands the target multiset so that the multiplicity of each element becomes the maximum
        of its multiplicities in the target and in other.
        Cost is O(m) operations where m is the other multiset's size.

        @param[in,out] target the multiset to update
        @param[in] other the multiset to union with - target itself is allowed and keeps it unchanged
        @return the number of elements added
      """) as m:
      m.code = lambda m: f"""
        size_t added;
        {r.definition};
        assert(target);
        assert({m.other});
        if(target == {m.other}) return 0;
        added = 0;
        for({r} = {range.new(m.other)}; !{range.empty(r)}; {range.move_front(r)}) {{
          if({self.count(m.target, range.front_view(r))} < {self.count(m.other, range.front_view(r))}) {{
            added += {self.put(m.target, range.front_view(r))};
          }}
        }}
        return added;
      """

    with self.method(std.size_t, ("apply", "difference"), {"target": inout(self), "other": self}, constraint=algebra_constraint, optional_group="algebraic_operations", brief="Multiset difference (subtract multiplicities)",
      description="""
        Subtracts the multiplicity of each element in other from the multiplicity in target.
        Cost is O(m) calls to `remove` where m is the other multiset's size.

        @param[in,out] target the multiset to subtract from
        @param[in] other the multiset whose occurrences are subtracted - target itself is allowed and empties it in place
        @return the number of elements removed
      """) as m:
      m.code = lambda m: f"""
        size_t removed;
        {r.definition};
        assert(target);
        assert({m.other});
        if(target == {m.other}) {{
          removed = {self.size(m.target)};
          {self.destroy(m.target)};
          {self.create(m.target)};
          return removed;
        }}
        removed = 0;
        for({r} = {range.new(m.other)}; !{range.empty(r)}; {range.move_front(r)}) {{
          removed += {self.remove(m.target, range.front_view(r))};
        }}
        return removed;
      """

    with self.method(std.size_t, ("apply", "intersection"), {"target": inout(self), "other": self}, constraint=algebra_constraint, optional_group="algebraic_operations", brief="Multiset intersection (minimum multiplicities)",
      description="""
        Reduces the multiplicity of each element in target to the minimum of its multiplicities
        in target and in other.
        Cost is O(n) operations where n is the target size plus copy cost.

        @param[in,out] target the multiset to intersect
        @param[in] other the multiset to intersect with - target itself is allowed and keeps it unchanged
        @return the number of elements removed
      """) as m:
      m.code = lambda m: f"""
        size_t removed;
        {r.definition};
        {temp.definition};
        assert(target);
        assert({m.other});
        if(target == {m.other}) return 0;
        {self.create(temp)};
        {self.copy(temp, m.target)};
        removed = 0;
        for({r} = {range.new(temp)}; !{range.empty(r)}; {range.move_front(r)}) {{
          if({self.count(m.target, range.front_view(r))} > {self.count(m.other, range.front_view(r))}) {{
            removed += {self.remove(m.target, range.front_view(r))};
          }}
        }}
        {self.destroy(temp)};
        return removed;
      """

    with self.method(std.size_t, ("apply", "symmetric", "difference"), {"target": inout(self), "other": self}, constraint=algebra_constraint, optional_group="algebraic_operations", brief="Multiset symmetric difference (absolute difference of multiplicities)",
      description="""
        Sets the multiplicity of each element in target to the absolute difference |m_target - m_other|.
        The target itself is allowed and empties it in place.

        @param[in,out] target the multiset to update
        @param[in] other the multiset to compare against
        @return the number of elements added or removed
      """) as m:
      m.code = lambda m: f"""
        size_t changed;
        {r.definition};
        {temp.definition};
        assert(target);
        assert({m.other});
        if(target == {m.other}) {{
          changed = {self.size(m.target)};
          {self.destroy(m.target)};
          {self.create(m.target)};
          return changed;
        }}
        {self.create(temp)};
        for({r} = {range.new(m.other)}; !{range.empty(r)}; {range.move_front(r)}) {{
          {self.put(temp, range.front_view(r))};
        }}
        for({r} = {range.new(m.target)}; !{range.empty(r)}; {range.move_front(r)}) {{
          {self.remove(temp, range.front_view(r))};
        }}
        changed = {self.apply_difference(m.target, m.other)};
        for({r} = {range.new(temp)}; !{range.empty(r)}; {range.move_front(r)}) {{
          changed += {self.put(m.target, range.front_view(r))};
        }}
        {self.destroy(temp)};
        return changed;
      """

    # --- Constructing algebraic operations on immutable sources ---

    with self.method(None, ("create", "union"), {"target": out(self), "left": self, "right": self}, constraint=algebra_constraint, optional_group="algebraic_operations", brief="Construct multiset union (maximum multiplicities)",
      description="""
        Constructs target with element multiplicities set to max(m_left(x), m_right(x)).
        The inputs are not modified.

        @param[out] target the uninitialized storage to construct
        @param[in] left the first multiset
        @param[in] right the second multiset
      """) as m:
      m.code = lambda m: f"""
        assert(target);
        assert({m.left});
        assert({m.right});
        assert(target != {m.left} && target != {m.right}); /* the target must be fresh storage */
        if({m.left} == {m.right}) {{
          {self.copy(m.target, m.left)};
          return;
        }}
        {r.definition};
        if({self.size(m.left)} >= {self.size(m.right)}) {{
          {self.copy(m.target, m.left)};
          for({r} = {range.new(m.right)}; !{range.empty(r)}; {range.move_front(r)}) {{
            if({self.count(m.target, range.front_view(r))} < {self.count(m.right, range.front_view(r))}) {{
              {self.put(m.target, range.front_view(r))};
            }}
          }}
        }} else {{
          {self.copy(m.target, m.right)};
          for({r} = {range.new(m.left)}; !{range.empty(r)}; {range.move_front(r)}) {{
            if({self.count(m.target, range.front_view(r))} < {self.count(m.left, range.front_view(r))}) {{
              {self.put(m.target, range.front_view(r))};
            }}
          }}
        }}
      """

    with self.method(None, ("create", "intersection"), {"target": out(self), "left": self, "right": self}, constraint=algebra_constraint, optional_group="algebraic_operations", brief="Construct multiset intersection (minimum multiplicities)",
      description="""
        Constructs target with element multiplicities set to min(m_left(x), m_right(x)).
        The inputs are not modified.

        @param[out] target the uninitialized storage to construct
        @param[in] left the first multiset
        @param[in] right the second multiset
      """) as m:
      m.code = lambda m: f"""
        assert(target);
        assert({m.left});
        assert({m.right});
        assert(target != {m.left} && target != {m.right}); /* the target must be fresh storage */
        if({m.left} == {m.right}) {{
          {self.copy(m.target, m.left)};
          return;
        }}
        {r.definition};
        {self.create(m.target)};
        if({self.size(m.left)} <= {self.size(m.right)}) {{
          for({r} = {range.new(m.left)}; !{range.empty(r)}; {range.move_front(r)}) {{
            if({self.count(m.target, range.front_view(r))} < {self.count(m.right, range.front_view(r))}) {{
              {self.put(m.target, range.front_view(r))};
            }}
          }}
        }} else {{
          for({r} = {range.new(m.right)}; !{range.empty(r)}; {range.move_front(r)}) {{
            if({self.count(m.target, range.front_view(r))} < {self.count(m.left, range.front_view(r))}) {{
              {self.put(m.target, range.front_view(r))};
            }}
          }}
        }}
      """

    with self.method(None, ("create", "difference"), {"target": out(self), "left": self, "right": self}, constraint=algebra_constraint, optional_group="algebraic_operations", brief="Construct multiset difference (subtract multiplicities)",
      description="""
        Constructs target with element multiplicities set to max(0, m_left(x) - m_right(x)).
        The inputs are not modified.

        @param[out] target the uninitialized storage to construct
        @param[in] left the multiset to subtract from
        @param[in] right the multiset whose multiplicities are subtracted
      """) as m:
      m.code = lambda m: f"""
        assert(target);
        assert({m.left});
        assert({m.right});
        assert(target != {m.left} && target != {m.right}); /* the target must be fresh storage */
        if({m.left} == {m.right}) {{
          {self.create(m.target)};
          return;
        }}
        if({self.size(m.right)} == 0) {{
          {self.copy(m.target, m.left)};
          return;
        }}
        {r.definition};
        {self.create(m.target)};
        for({r} = {range.new(m.left)}; !{range.empty(r)}; {range.move_front(r)}) {{
          size_t c_l = {self.count(m.left, range.front_view(r))};
          size_t c_r = {self.count(m.right, range.front_view(r))};
          if(c_l > c_r && {self.count(m.target, range.front_view(r))} < c_l - c_r) {{
            {self.put(m.target, range.front_view(r))};
          }}
        }}
      """

    with self.method(None, ("create", "symmetric", "difference"), {"target": out(self), "left": self, "right": self}, constraint=algebra_constraint, optional_group="algebraic_operations", brief="Construct multiset symmetric difference (|m_left - m_right|)",
      description="""
        Constructs target with element multiplicities set to |m_left(x) - m_right(x)|.
        The inputs are not modified.

        @param[out] target the uninitialized storage to construct
        @param[in] left the first multiset
        @param[in] right the second multiset
      """) as m:
      m.code = lambda m: f"""
        assert(target);
        assert({m.left});
        assert({m.right});
        assert(target != {m.left} && target != {m.right}); /* the target must be fresh storage */
        if({m.left} == {m.right}) {{
          {self.create(m.target)};
          return;
        }}
        {r.definition};
        {self.create(m.target)};
        for({r} = {range.new(m.left)}; !{range.empty(r)}; {range.move_front(r)}) {{
          size_t c_l = {self.count(m.left, range.front_view(r))};
          size_t c_r = {self.count(m.right, range.front_view(r))};
          if(c_l > c_r && {self.count(m.target, range.front_view(r))} < c_l - c_r) {{
            {self.put(m.target, range.front_view(r))};
          }}
        }}
        for({r} = {range.new(m.right)}; !{range.empty(r)}; {range.move_front(r)}) {{
          size_t c_r = {self.count(m.right, range.front_view(r))};
          size_t c_l = {self.count(m.left, range.front_view(r))};
          if(c_r > c_l && {self.count(m.target, range.front_view(r))} < c_r - c_l) {{
            {self.put(m.target, range.front_view(r))};
          }}
        }}
      """

    with self.method("int", ("is", "subset"), {"target": self, "other": self}, constraint=subset_constraint, optional_group="algebraic_operations", brief="Check if target is a sub-multiset of other",
      description="""
        Checks whether for every element in target, its multiplicity in target does not exceed
        its multiplicity in other.

        @param[in] target the candidate sub-multiset
        @param[in] other the candidate super-multiset
        @return non-zero if target is a sub-multiset of other, zero otherwise
      """) as m:
      m.code = lambda m: f"""
        {r.definition};
        assert(target);
        assert({m.other});
        if(target == {m.other}) return 1;
        if({self.size(m.target)} > {self.size(m.other)}) return 0;
        for({r} = {range.new(m.target)}; !{range.empty(r)}; {range.move_front(r)}) {{
          if({self.count(m.target, range.front_view(r))} > {self.count(m.other, range.front_view(r))}) return 0;
        }}
        return 1;
      """

    with self.method("int", ("is", "superset"), {"target": self, "other": self}, constraint=subset_constraint, optional_group="algebraic_operations", brief="Check if target is a super-multiset of other",
      description="""
        Checks whether for every element in other, its multiplicity in other does not exceed
        its multiplicity in target.

        @param[in] target the candidate super-multiset
        @param[in] other the candidate sub-multiset
        @return non-zero if target is a super-multiset of other, zero otherwise
      """) as m:
      m.code = lambda m: f"""
        {r.definition};
        assert(target);
        assert({m.other});
        if(target == {m.other}) return 1;
        if({self.size(m.other)} > {self.size(m.target)}) return 0;
        for({r} = {range.new(m.other)}; !{range.empty(r)}; {range.move_front(r)}) {{
          if({self.count(m.other, range.front_view(r))} > {self.count(m.target, range.front_view(r))}) return 0;
        }}
        return 1;
      """
