from autoc.core import inout, out, enforced, Comparable, Coerce
from autoc.traversable import Traversable
from autoc.insertable import Insertable


# Abstract base for all set collections
class Set(Traversable, Insertable):

  @enforced
  def __init__(self, name: str, element: Coerce[Comparable], *args, algebraic_operations=True, **kwargs):
    self.algebraic_operations = bool(algebraic_operations)
    super().__init__(name, element, *args, **kwargs)

  def __setup__(self):
    super().__setup__()

    self.method("int", "put", {"target": inout(self), "element": self.element}, constraint=lambda: self.element.copyable and self.element.comparable, brief="Insert element if not present",
      description="""
        Inserts the element when the set holds no equal element yet. Every set implementation
        inherits this protocol operation. The insertion cost matches the underlying
        implementation: expected O(1) for hash-based sets, expected O(log n) for tree-based sets.

        @param[in,out] target the set to insert into
        @param[in] element the element to insert - ignored when the set already holds an equal element
        @return non-zero if the element was inserted and zero if an equal element was already present
      """)

    self.method("int", "emplace", {"target": inout(self)} | self.element.constructor_parameters,
      constraint=lambda: self.element.emplaceable and self.element.comparable,
      brief="Construct element in-place if not present",
      description="""
        Constructs an element in-place with forwarded parameters and inserts it into the set
        if no equal element is present yet.
        Returns non-zero if the element was inserted and zero if an equal element was already present.

        @param[in,out] target the set to insert into
        @return non-zero if the element was inserted and zero if an equal element was already present
      """)

    self.method("int", "remove", {"target": inout(self), "element": self.element}, constraint=lambda: self.element.comparable, brief="Remove element if present",
      description="""
        Removes the element when the set holds an equal one, leaving the set unchanged
        otherwise. Every set implementation inherits this protocol operation. The removal
        cost matches the underlying implementation: expected O(1) for hash-based sets,
        expected O(log n) for tree-based sets.

        @param[in,out] target the set to remove from
        @param[in] element the element to remove
        @return non-zero if the element was removed and zero if the set held no equal element
      """)

    # The algebraic operations are composed entirely out of the protocol primitives so every
    # set implementation inherits them. They mutate the target in place and return the number
    # of the elements added, removed or changed. The bodies are built lazily because they call
    # the put/remove/contains operations which are inactive for the elements failing the traits.
    # The other set is the second operand - the self operations are shortcut
    range = self.range
    r = range.variable("r")
    temp = self.variable("temp")
    algebra_constraint = lambda: self.algebraic_operations and self.element.copyable and self.element.comparable
    subset_constraint = lambda: self.algebraic_operations and self.element.comparable

    with self.method("int", ("apply", "union"), {"target": inout(self), "other": self}, constraint=algebra_constraint, optional_group="algebraic_operations", brief="Add all elements from other set",
      description="""
        Adds every element of the other set which the target does not hold yet by walking
        the other set's range and putting its elements. The other set is not modified.
        Cost is O(m) calls to `put` where m is the other set's size.

        @param[in,out] target the set to add the elements to
        @param[in] other the set whose elements are added - the target itself is allowed and keeps it unchanged
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
          added += {self.put(m.target, range.front_view(r))};
        }}
        return added;
      """

    with self.method("int", ("apply", "difference"), {"target": inout(self), "other": self}, constraint=algebra_constraint, optional_group="algebraic_operations", brief="Remove all elements found in other set",
      description="""
        Removes every element of the target which the other set holds by walking the other
        set's range and removing its elements. The other set is not modified.
        Cost is O(m) calls to `remove` where m is the other set's size.

        @param[in,out] target the set to remove the elements from
        @param[in] other the set whose elements are removed - the target itself is allowed and empties it in place
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

    with self.method("int", ("apply", "intersection"), {"target": inout(self), "other": self}, constraint=algebra_constraint, optional_group="algebraic_operations", brief="Keep only elements also present in other set",
      description="""
        Removes every element of the target which the other set does not hold. The other set
        is traversed via a temporary copy of the target so the removals do not disturb the walk.
        Cost is O(n) calls to `contains` and `remove` where n is the target size plus the cost
        of copying the target.

        @param[in,out] target the set to keep the elements in
        @param[in] other the set to intersect with - the target itself is allowed and keeps it unchanged
        @return the number of elements removed
      """) as m:
      m.code = lambda m: f"""
        size_t removed;
        {r.definition};
        {temp.definition};
        assert(target);
        assert({m.other});
        if(target == {m.other}) return 0; /* nothing is removed intersecting with self */
        {self.create(temp)};
        {self.copy(temp, m.target)};
        removed = 0;
        for({r} = {range.new(temp)}; !{range.empty(r)}; {range.move_front(r)}) {{
          if(!{self.contains(m.other, range.front_view(r))}) removed += {self.remove(m.target, range.front_view(r))};
        }}
        {self.destroy(temp)};
        return removed;
      """

    with self.method("int", ("apply", "symmetric", "difference"), {"target": inout(self), "other": self}, constraint=algebra_constraint, optional_group="algebraic_operations", brief="Remove elements in both sets, add elements in only one",
      description="""
        Removes the elements the two sets share and adds the elements only the other set
        holds, making the target hold the elements present in exactly one of the sets.
        Cost is O(m) calls to `contains`, `remove`, and `put` where m is the other set's size.

        @param[in,out] target the set to change
        @param[in] other the set to change the target by - the target itself is allowed and empties it in place
        @return the number of elements added or removed
      """) as m:
      m.code = lambda m: f"""
        size_t changed;
        {r.definition};
        assert(target);
        assert({m.other});
        if(target == {m.other}) {{
          changed = {self.size(m.target)};
          {self.destroy(m.target)};
          {self.create(m.target)};
          return changed;
        }}
        changed = 0;
        for({r} = {range.new(m.other)}; !{range.empty(r)}; {range.move_front(r)}) {{
          if({self.contains(m.target, range.front_view(r))}) changed += {self.remove(m.target, range.front_view(r))};
          else changed += {self.put(m.target, range.front_view(r))};
        }}
        return changed;
      """

    # --- Constructing algebraic operations on immutable sources ---

    with self.method(None, ("create", "union"), {"target": out(self), "left": self, "right": self}, constraint=algebra_constraint, optional_group="algebraic_operations", brief="Construct union of two sets",
      description="""
        Constructs the target set as the union of left and right, holding every element
        present in either left or right. The inputs are not modified.

        @param[out] target the uninitialized storage to construct
        @param[in] left the first set
        @param[in] right the second set
      """) as m:
      m.code = lambda m: f"""
        {r.definition};
        assert(target);
        assert({m.left});
        assert({m.right});
        if({m.left} == {m.right}) {{
          {self.copy(m.target, m.left)};
          return;
        }}
        if({self.size(m.left)} >= {self.size(m.right)}) {{
          {self.copy(m.target, m.left)};
          for({r} = {range.new(m.right)}; !{range.empty(r)}; {range.move_front(r)}) {{
            {self.put(m.target, range.front_view(r))};
          }}
        }} else {{
          {self.copy(m.target, m.right)};
          for({r} = {range.new(m.left)}; !{range.empty(r)}; {range.move_front(r)}) {{
            {self.put(m.target, range.front_view(r))};
          }}
        }}
      """

    with self.method(None, ("create", "intersection"), {"target": out(self), "left": self, "right": self}, constraint=algebra_constraint, optional_group="algebraic_operations", brief="Construct intersection of two sets",
      description="""
        Constructs the target set as the intersection of left and right, holding every element
        present in both left and right. The inputs are not modified.

        @param[out] target the uninitialized storage to construct
        @param[in] left the first set
        @param[in] right the second set
      """) as m:
      m.code = lambda m: f"""
        {r.definition};
        assert(target);
        assert({m.left});
        assert({m.right});
        if({m.left} == {m.right}) {{
          {self.copy(m.target, m.left)};
          return;
        }}
        {self.create(m.target)};
        if({self.size(m.left)} <= {self.size(m.right)}) {{
          for({r} = {range.new(m.left)}; !{range.empty(r)}; {range.move_front(r)}) {{
            if({self.contains(m.right, range.front_view(r))}) {{
              {self.put(m.target, range.front_view(r))};
            }}
          }}
        }} else {{
          for({r} = {range.new(m.right)}; !{range.empty(r)}; {range.move_front(r)}) {{
            if({self.contains(m.left, range.front_view(r))}) {{
              {self.put(m.target, range.front_view(r))};
            }}
          }}
        }}
      """

    with self.method(None, ("create", "difference"), {"target": out(self), "left": self, "right": self}, constraint=algebra_constraint, optional_group="algebraic_operations", brief="Construct difference of two sets",
      description="""
        Constructs the target set as the difference of left and right (left \\ right), holding
        every element present in left but not in right. The inputs are not modified.

        @param[out] target the uninitialized storage to construct
        @param[in] left the set of elements to keep
        @param[in] right the set of elements to exclude
      """) as m:
      m.code = lambda m: f"""
        {r.definition};
        assert(target);
        assert({m.left});
        assert({m.right});
        if({m.left} == {m.right}) {{
          {self.create(m.target)};
          return;
        }}
        if({self.size(m.right)} == 0) {{
          {self.copy(m.target, m.left)};
          return;
        }}
        {self.create(m.target)};
        for({r} = {range.new(m.left)}; !{range.empty(r)}; {range.move_front(r)}) {{
          if(!{self.contains(m.right, range.front_view(r))}) {{
            {self.put(m.target, range.front_view(r))};
          }}
        }}
      """

    with self.method(None, ("create", "symmetric", "difference"), {"target": out(self), "left": self, "right": self}, constraint=algebra_constraint, optional_group="algebraic_operations", brief="Construct symmetric difference of two sets",
      description="""
        Constructs the target set as the symmetric difference of left and right, holding
        elements present in exactly one of the sets. The inputs are not modified.

        @param[out] target the uninitialized storage to construct
        @param[in] left the first set
        @param[in] right the second set
      """) as m:
      m.code = lambda m: f"""
        {r.definition};
        assert(target);
        assert({m.left});
        assert({m.right});
        {self.create(m.target)};
        if({m.left} == {m.right}) return;
        for({r} = {range.new(m.left)}; !{range.empty(r)}; {range.move_front(r)}) {{
          if(!{self.contains(m.right, range.front_view(r))}) {{
            {self.put(m.target, range.front_view(r))};
          }}
        }}
        for({r} = {range.new(m.right)}; !{range.empty(r)}; {range.move_front(r)}) {{
          if(!{self.contains(m.left, range.front_view(r))}) {{
            {self.put(m.target, range.front_view(r))};
          }}
        }}
      """

    with self.method("int", ("is", "subset"), {"target": self, "other": self}, constraint=subset_constraint, optional_group="algebraic_operations", brief="Check if all elements are in other set",
      description="""
        Walks the target's range and looks every element up in the other set, aborting on
        the first missing one.

        @param[in] target the set to test
        @param[in] other the set to test against
        @return non-zero if every element of the target is also present in the other set
      """) as m:
      m.code = lambda m: f"""
        {r.definition};
        assert(target);
        assert({m.other});
        for({r} = {range.new(m.target)}; !{range.empty(r)}; {range.move_front(r)}) {{
          if(!{self.contains(m.other, range.front_view(r))}) return 0;
        }}
        return 1;
      """

    with self.method("int", ("is", "superset"), {"target": self, "other": self}, constraint=subset_constraint, optional_group="algebraic_operations", brief="Check if all elements of other are in this set",
      description="""
        Walks the other set's range and looks every element up in the target, aborting on
        the first missing one.

        @param[in] target the set to test against
        @param[in] other the set to test
        @return non-zero if every element of the other set is also present in the target
      """) as m:
      m.code = lambda m: f"""
        {r.definition};
        assert(target);
        assert({m.other});
        for({r} = {range.new(m.other)}; !{range.empty(r)}; {range.move_front(r)}) {{
          if(!{self.contains(m.target, range.front_view(r))}) return 0;
        }}
        return 1;
      """

    # TODO pop, ...
