import metac.std as std
from metac.hash import XorRot
from metac.assignable import Assignable
from metac.sortable import Sortable
from metac.sequential import Sequential
from metac.insertable import Insertable
from metac.range import DirectAccess
from metac.container import _Range
from metac.core import out, inout, Callable, Indirection, _StructRenderer


#
class Packet(_StructRenderer, Assignable, Sortable, Sequential, Insertable):

  brief = "Fixed-capacity stack-allocated direct access sequence container"

  def __init__(self, name, element, capacity, *args, index=std.size_t, sorting_operations=True, hasher=XorRot(), dependencies=(), **kwargs):
    self._capacity = int(capacity)
    if self._capacity < 1:
      raise ValueError(f"Capacity must be at least 1, got {self._capacity}")
    super().__init__(name, element, index, *args, sorting_operations=sorting_operations, hasher=hasher, dependencies=(*dependencies, std.assert_h, std.string_h), **kwargs)
    self.range = Range(self)

  @property
  def constructible(self):
    return True

  @property
  def default_constructible(self):
    return True

  @property
  def destructible(self):
    return self.element.destructible

  @property
  def copyable(self):
    return self.element.copyable

  @property
  def moveable(self):
    return self.element.moveable

  @property
  def swappable(self):
    return self.element.swappable

  @property
  def comparable(self):
    return self.element.comparable

  @property
  def orderable(self):
    return False

  @property
  def hashable(self):
    return self.element.hashable

  @property
  def zero_initializable(self):
    return True

  def _element(self, target, index):
    return self.element.variable(f"{target}->elements[{index}]")

  def _target_size(self, target):
    return f"{target}->size"

  def _render_struct(self, stream, header):
    super()._render_struct(stream, header)
    stream.append(f"""
      struct {self.name} {{
        {self.element} elements[{self._capacity}]; /**< @private */
        size_t size; /**< @private */
      }};
    """)

  def __setup__(self):
    super().__setup__()

    self.description = f"""
      Fixed-capacity direct access sequence container with maximum capacity of {self._capacity} elements.
      Allocates no dynamic heap memory, storing elements inline in a contiguous C array.
      Supports bidirectional element traversal via the corresponding @ref {self.range} iterator
      as well as direct indexed access, sorting, and binary search over its elements.

      The closest C++ equivalent is [std::inplace_vector<>](https://en.cppreference.com/w/cpp/container/inplace_vector) (C++26)
      or [boost::container::static_vector<>](https://www.boost.org/doc/libs/release/doc/html/container/non_standard_containers.html#container.non_standard_containers.static_vector).
    """

    target_i = self.element.variable("target->elements[index]")
    source_i = self.element.variable("source->elements[index]")
    left_i = self.element.variable("left->elements[index]")
    right_i = self.element.variable("right->elements[index]")
    destroy_i = f"{self.element.destroy(target_i)};" if self.element.destructible else ""

    with self.empty as m:
      m.inline_code = f"""
        assert(target);
        return target->size == 0;
      """

    with self.size as m:
      m.inline_code = f"""
        assert(target);
        return target->size;
      """

    with self.method(self.index, "capacity", {"target": self}, brief="Get maximum capacity of static vector",
      description="""
        Returns the maximum number of elements the static vector can hold.

        @param[in] target the static vector to inspect
        @return maximum capacity of the vector
      """) as m:
      m.inline_code = f"""
        assert(target);
        return {self._capacity};
      """

    with self.method("int", "full", {"target": self}, brief="Check if static vector is at maximum capacity",
      description="""
        Checks whether the number of elements in the static vector has reached its capacity.

        @param[in] target the static vector to inspect
        @return non-zero if full, zero otherwise
      """) as m:
      m.inline_code = f"""
        assert(target);
        return target->size == {self._capacity};
      """

    with self.indexed as m:
      m.inline_code = f"""
        assert(target);
        return {m.index} < target->size;
      """

    with self.create as m:
      m.inline_code = f"""
        assert(target);
        target->size = 0;
      """

    with self.method(None, ("create", "size"), {"target": out(self), "size": self.index},
      constraint=lambda: self.element.default_constructible or self.element.zero_initializable,
      brief="Create static vector with the given number of default-initialized elements",
      description="""
        Creates the static vector holding exactly the given number of default-initialized elements.
        The size must not exceed the capacity.

        @param[out] target the static vector to construct
        @param[in] size the number of default-initialized elements to create
      """) as m:
      if self.element.zero_initializable:
        m.code = f"""
          assert(target);
          assert({m.size} <= {self._capacity});
          target->size = {m.size};
          memset(target->elements, 0, {m.size} * sizeof(target->elements[0]));
        """
      else:
        m.code = f"""
          size_t index;
          assert(target);
          assert({m.size} <= {self._capacity});
          target->size = {m.size};
          for(index = 0; index < {m.size}; ++index) {{
            {self.element.create(target_i)};
          }}
        """

    if self.destructible:
      with self.destroy as m:
        m.code = f"""
          size_t index;
          assert(target);
          for(index = 0; index < target->size; ++index) {{
            {self.element.destroy(target_i)};
          }}
        """

    with self.copy as m:
      m.code = lambda m: f"""
        size_t index;
        assert(target);
        assert(source);
        if(target == source) return;
        target->size = source->size;
        for(index = 0; index < source->size; ++index) {{
          {self.element.copy(target_i, source_i)};
        }}
      """

    with self.move as m:
      move_elem = f"{self.element.move(target_i, source_i)};" if self.element.moveable else f"{self.element.copy(target_i, source_i)}; {self.element.destroy(source_i) if self.element.destructible else ''}"
      m.code = lambda m: f"""
        size_t index;
        assert(target);
        assert(source);
        if(target == source) return;
        target->size = source->size;
        for(index = 0; index < source->size; ++index) {{
          {move_elem}
        }}
        source->size = 0;
      """

    with self.swap as m:
      move_left_to_right = f"{self.element.move(right_i, left_i)};" if self.element.moveable else f"{self.element.copy(right_i, left_i)}; {self.element.destroy(left_i) if self.element.destructible else ''}"
      move_right_to_left = f"{self.element.move(left_i, right_i)};" if self.element.moveable else f"{self.element.copy(left_i, right_i)}; {self.element.destroy(right_i) if self.element.destructible else ''}"
      m.code = f"""
        size_t index, min_size, temp_size;
        assert(left);
        assert(right);
        if(left == right) return;
        min_size = left->size < right->size ? left->size : right->size;
        for(index = 0; index < min_size; ++index) {{
          {self.element.swap(left_i, right_i)};
        }}
        if(left->size > right->size) {{
          for(index = min_size; index < left->size; ++index) {{
            {move_left_to_right}
          }}
        }} else if(right->size > left->size) {{
          for(index = min_size; index < right->size; ++index) {{
            {move_right_to_left}
          }}
        }}
        temp_size = left->size;
        left->size = right->size;
        right->size = temp_size;
      """

    with self.get as m:
      result = m.result.variable("result")
      m.inline_code = lambda m: f"""
        {result.definition};
        assert(target);
        assert({self.indexed(m.target, m.index)});
        {self.element.copy(result, self._element(m.target, m.index))};
        return {result};
      """

    with self.view as m:
      m.inline_code = lambda m: f"""
        assert(target);
        assert({self.indexed(m.target, m.index)});
        return {self._element(m.target, m.index).bind(m.result)};
      """

    with self.set as m:
      def _set(m):
        slot = self._element(m.target, m.index)
        destroy_slot = f"{self.element.destroy(slot)};" if self.element.destructible else ""
        return f"""
          assert(target);
          assert({self.indexed(m.target, m.index)});
          {destroy_slot}
          {self.element.copy(slot, m.element)};
        """
      m.inline_code = _set

    with self.method(None, "emplace", {"target": inout(self), "index": self.index} | self.element.constructor_parameters,
      constraint=lambda: self.element.emplaceable, brief="Construct the element at index in place",
      description="""
        Constructs the element in place with the forwarded parameters, associating it with
        the index - the element previously held at the index is destroyed first.

        @param[in,out] target the static vector to update
        @param[in] index the index to construct the element at
      """) as m:
      def _emplace_code(m):
        create_args = [getattr(m, name) for name in self.element.constructor_parameters]
        slot = self._element(m.target, m.index)
        destroy_slot = f"{self.element.destroy(slot)};" if self.element.destructible else ""
        return f"""
          assert(target);
          assert({self.indexed(m.target, m.index)});
          {destroy_slot}
          {self.element.create(slot, *create_args)};
        """
      m.code = _emplace_code

    with self.method(None, "push", {"target": inout(self), "element": self.element},
      constraint=lambda: self.element.copyable, brief="Add element to back of static vector",
      description="""
        Appends the element to the back of the static vector in O(1). Asserts that the vector
        has not reached its maximum capacity.

        @param[in,out] target the static vector to add to
        @param[in] element the element to push to the back
      """) as m:
      m.inline_code = lambda m: f"""
        assert(target);
        assert(target->size < {self._capacity});
        {self.element.copy(self.element.variable("target->elements[target->size]"), m.element)};
        ++target->size;
      """

    with self.method(None, ("emplace", "back"), {"target": inout(self)} | self.element.constructor_parameters,
      constraint=lambda: self.element.emplaceable, brief="Construct element in-place at back of static vector",
      description="""
        Constructs the element in-place with forwarded parameters at the back of the static vector in O(1).
        Asserts that the vector has not reached its maximum capacity.

        @param[in,out] target the static vector to add to
      """) as m:
      def _emplace_back(m):
        create_args = [getattr(m, name) for name in self.element.constructor_parameters]
        slot = self.element.variable("target->elements[target->size]")
        return f"""
          assert(target);
          assert(target->size < {self._capacity});
          {self.element.create(slot, *create_args)};
          ++target->size;
        """
      m.inline_code = _emplace_back

    self.macro("emplace", None, {"target": inout(self)} | self.element.constructor_parameters,
      lambda target, *args: self.emplace_back(target, *args),
      constraint=lambda: self.element.emplaceable, brief="Construct element in-place at back (synonym for emplace_back)")

    with self.method(self.element, "pop", {"target": inout(self)}, constraint=lambda: self.element.moveable, brief="Remove and return element from back of static vector",
      description="""
        Removes and returns the back element in O(1). The vector must not be empty.

        @param[in,out] target the static vector to remove from
        @return the removed back element
      """) as m:
      result = m.result.variable("result")
      last_slot = self.element.variable("target->elements[target->size]")
      m.inline_code = f"""
        {result.definition};
        assert(target);
        assert(target->size > 0);
        --target->size;
        {self.element.move(result, last_slot)};
        return {result};
      """

    with self.put as m:
      m.inline_code = f"""
        assert(target);
        {self.push(m.target, m.element)};
        return 1;
      """

    target_next_i = self.element.variable("target->elements[index + 1]")
    with self.remove as m:
      def _remove(m):
        destroy_next = f"{self.element.destroy(target_next_i)};" if self.element.destructible else ""
        move_shift = (
          f"{self.element.move(target_i, target_next_i)};"
          if self.element.moveable else
          f"{self.element.copy(target_i, target_next_i)}; {destroy_next}"
        )
        return f"""
          size_t index;
          assert(target);
          for(index = 0; index < target->size; ++index) {{
            if({self.element.equal(target_i, m.element)}) {{
              {destroy_i}
              for(; index + 1 < target->size; ++index) {{
                {move_shift}
              }}
              --target->size;
              return 1;
            }}
          }}
          return 0;
        """
      m.code = _remove

    with self.method(None, "clear", {"target": inout(self)}, brief="Clear all elements from static vector",
      description="""
        Destroys all elements currently held by the static vector and resets it to the empty state.

        @param[in,out] target the static vector to clear
      """) as m:
      destroy_clear = f"""for(index = 0; index < target->size; ++index) {{
          {destroy_i}
        }}""" if self.element.destructible else ""
      m.code = f"""
        size_t index;
        assert(target);
        {destroy_clear}
        target->size = 0;
      """

    with self.method(self.element, "front", {"target": self}, constraint=lambda: self.element.copyable,
      references=(self.get,),
      brief="Get a copy of the front element",
      description="""
        Returns a copy of the first element in the static vector. The vector must not be empty.

        @param[in] target the static vector to read from
        @return a copy of the first element
      """) as m:
      m.inline_code = lambda m: f"""
        assert(target);
        assert(!{self.empty(m.target)});
        return {self.get(m.target, 0)};
      """

    with self.method(self.element.view_type, ("front", "view"), {"target": self},
      references=(self.view,),
      brief="Get a constant view of the front element",
      description="""
        Returns a constant view of the first element in the static vector without copying it.
        The vector must not be empty.

        @param[in] target the static vector to read from
        @return a constant view of the first element
      """) as m:
      m.inline_code = f"""
        assert(target);
        assert(!{self.empty(m.target)});
        return {self.view(m.target, 0)};
      """

    with self.method(self.element, "back", {"target": self}, constraint=lambda: self.element.copyable,
      references=(self.get,),
      brief="Get a copy of the back element",
      description="""
        Returns a copy of the last element in the static vector. The vector must not be empty.

        @param[in] target the static vector to read from
        @return a copy of the last element
      """) as m:
      m.inline_code = lambda m: f"""
        assert(target);
        assert(!{self.empty(m.target)});
        return {self.get(m.target, "target->size - 1")};
      """

    with self.method(self.element.view_type, ("back", "view"), {"target": self},
      references=(self.view,),
      brief="Get a constant view of the back element",
      description="""
        Returns a constant view of the last element in the static vector without copying it.
        The vector must not be empty.

        @param[in] target the static vector to read from
        @return a constant view of the last element
      """) as m:
      m.inline_code = f"""
        assert(target);
        assert(!{self.empty(m.target)});
        return {self.view(m.target, "target->size - 1")};
      """

    with self.method(Indirection(self.element), "data", {"target": inout(self)}, brief="Get pointer to the underlying array",
      description="""
        Returns a pointer to the contiguous array storage.

        @param[in,out] target the static vector to inspect
        @return a pointer to the first element
      """) as m:
      m.inline_code = f"""
        assert(target);
        return target->elements;
      """


#
class Range(_Range, DirectAccess):

  brief = "Direct access range over static vector"

  def _render_struct(self, stream, header):
    super()._render_struct(stream, header)
    stream.append(f"""
      struct {self.name} {{
        {Indirection(self.iterable, constant=True)} iterable; /**< @private */
        {self.iterable.index} front, /**< @private */ back; /**< @private */
      }};
    """)

  def __setup__(self):
    super().__setup__()

    with self.method(Callable.Parameter(self), "new", {"iterable": self.iterable}, brief="Create range spanning the static vector",
      description="""
        Creates a range over the static vector elements. The range must not outlive the vector.

        @param[in] iterable the static vector to span
        @return the range covering the static vector
      """) as m:
      result = m.result.variable("result")
      m.inline_code = f"""
        {result.definition};
        assert(iterable);
        result.iterable = iterable;
        result.front = 0;
        result.back = iterable->size;
        return {result};
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
        return {self.iterable.get("target->iterable", "target->back - 1")};
      """

    with self.back_view as m:
      m.inline_code = lambda: f"""
        assert(target);
        assert(!{self.empty(m.target)});
        return {self.iterable.view("target->iterable", "target->back - 1")};
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
