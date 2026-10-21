import metac.std as std
from metac.hash import XorRot
from metac.assignable import Assignable
from metac.sortable import Sortable
from metac.sequential import Sequential
from metac.range import DirectAccess
from metac.container import _Range
from metac.core import inout, Callable, Indirection, _StructRenderer


#
class Array(_StructRenderer, Assignable, Sortable, Sequential):

  brief = "Fixed-size stack-allocated contiguous sequence container"

  def __init__(self, name, element, size, *args, index=std.size_t, sorting_operations=True, hasher=XorRot(), dependencies=(), **kwargs):
    self._size = int(size)
    if self._size < 1:
      raise ValueError(f"Array size must be at least 1, got {self._size}")
    super().__init__(name, element, index, *args, sorting_operations=sorting_operations, hasher=hasher, dependencies=(*dependencies, std.assert_h, std.string_h), **kwargs)
    self.range = Range(self)

  @property
  def constructible(self):
    return True

  @property
  def default_constructible(self):
    return self.element.default_constructible or self.element.zero_initializable

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
    return self.element.zero_initializable

  def _element(self, target, index):
    return self.element.variable(f"{target}->elements[{index}]")

  def _target_size(self, target):
    return str(self._size)

  def _render_struct(self, stream, header):
    super()._render_struct(stream, header)
    stream.append(f"""
      struct {self.name} {{
        {self.element} elements[{self._size}]; /**< @private */
      }};
    """)

  def __setup__(self):
    super().__setup__()

    self.description = f"""
      Fixed-size direct access sequence container holding exactly {self._size} elements.
      Allocates no dynamic heap memory, storing elements inline in a contiguous C array.
      Supports bidirectional element traversal via the corresponding @ref {self.range} iterator
      as well as direct indexed access to its elements.

      The closest C++ equivalent is [std::array<>](https://en.cppreference.com/w/cpp/container/array).
    """

    target_i = self.element.variable("target->elements[index]")
    source_i = self.element.variable("source->elements[index]")
    left_i = self.element.variable("left->elements[index]")
    right_i = self.element.variable("right->elements[index]")

    with self.empty as m:
      m.inline_code = f"""
        assert(target);
        return 0;
      """

    with self.size as m:
      m.inline_code = f"""
        assert(target);
        return {self._size};
      """

    with self.indexed as m:
      m.inline_code = f"""
        assert(target);
        return {m.index} < {self._size};
      """

    with self.create as m:
      if self.element.zero_initializable:
        m.inline_code = f"""
          assert(target);
          memset(target->elements, 0, sizeof(target->elements));
        """
      else:
        m.code = f"""
          size_t index;
          assert(target);
          for(index = 0; index < {self._size}; ++index) {{
            {self.element.create(target_i)};
          }}
        """

    with self.method(None, "fill", {"target": inout(self), "element": self.element}, constraint=lambda: self.element.copyable, brief="Fill all array elements with a copy of the given value",
      description="""
        Assigns the given value to every element of the array. Previous elements are destroyed if needed.

        @param[in,out] target the array to fill
        @param[in] element the value to assign to every position
      """) as m:
      destroy_i = self.element.destroy(target_i) if self.element.destructible else ""
      m.code = lambda m: f"""
        size_t index;
        assert(target);
        for(index = 0; index < {self._size}; ++index) {{
          {destroy_i};
          {self.element.copy(target_i, m.element)};
        }}
      """

    if self.destructible:
      with self.destroy as m:
        m.code = f"""
          size_t index;
          assert(target);
          for(index = 0; index < {self._size}; ++index) {{
            {self.element.destroy(target_i)};
          }}
        """

    with self.copy as m:
      m.code = lambda m: f"""
        size_t index;
        assert(target);
        assert(source);
        for(index = 0; index < {self._size}; ++index) {{
          {self.element.copy(target_i, source_i)};
        }}
      """

    with self.move as m:
      m.code = f"""
        size_t index;
        assert(target);
        assert(source);
        for(index = 0; index < {self._size}; ++index) {{
          {self.element.move(target_i, source_i)};
        }}
      """

    with self.swap as m:
      m.code = f"""
        size_t index;
        assert(left);
        assert(right);
        for(index = 0; index < {self._size}; ++index) {{
          {self.element.swap(left_i, right_i)};
        }}
      """

    with self.get as m:
      result = m.result.variable("result")
      slot = self.element.variable(f"target->elements[{m.index}]")
      m.inline_code = lambda m: f"""
        {result.definition};
        assert(target);
        assert({self.indexed(m.target, m.index)});
        {self.element.copy(result, slot)};
        return {result};
      """

    with self.view as m:
      slot = self.element.variable(f"target->elements[{m.index}]")
      m.inline_code = f"""
        assert(target);
        assert({self.indexed(m.target, m.index)});
        return {slot.bind(m.result)};
      """

    with self.set as m:
      slot = self.element.variable(f"target->elements[{m.index}]")
      destroy_slot = self.element.destroy(slot) if self.element.destructible else ""
      m.inline_code = lambda m: f"""
        assert(target);
        assert({self.indexed(m.target, m.index)});
        {destroy_slot};
        {self.element.copy(slot, m.element)};
      """

    with self.method(None, "emplace", {"target": inout(self), "index": self.index} | self.element.constructor_parameters,
      constraint=lambda: self.element.emplaceable, brief="Construct the element at index in place",
      description="""
        Constructs the element in place with the forwarded parameters, associating it with
        the index - the element previously held at the index is destroyed first.

        @param[in,out] target the array to update
        @param[in] index the index to construct the element at
      """) as m:
      def _emplace_code(m):
        create_args = [getattr(m, name) for name in self.element.constructor_parameters]
        slot = self.element.variable(f"target->elements[{m.index}]")
        destroy_slot = self.element.destroy(slot) if self.element.destructible else ""
        return f"""
          assert(target);
          assert({self.indexed(m.target, m.index)});
          {destroy_slot};
          {self.element.create(slot, *create_args)};
        """
      m.code = _emplace_code

    with self.method(self.element, "front", {"target": self}, constraint=lambda: self.element.copyable,
      references=(self.get,),
      brief="Get a copy of the front element",
      description="""
        Returns a copy of the first element in the array.

        @param[in] target the array to read from
        @return a copy of the first element
      """) as m:
      m.inline_code = lambda m: f"""
        assert(target);
        return {self.get(m.target, 0)};
      """

    with self.method(self.element.view_type, ("front", "view"), {"target": self},
      references=(self.view,),
      brief="Get a constant view of the front element",
      description="""
        Returns a constant view of the first element in the array without copying it.

        @param[in] target the array to read from
        @return a constant view of the first element
      """) as m:
      m.inline_code = f"""
        assert(target);
        return {self.view(m.target, 0)};
      """

    with self.method(self.element, "back", {"target": self}, constraint=lambda: self.element.copyable,
      references=(self.get,),
      brief="Get a copy of the back element",
      description="""
        Returns a copy of the last element in the array.

        @param[in] target the array to read from
        @return a copy of the last element
      """) as m:
      m.inline_code = lambda m: f"""
        assert(target);
        return {self.get(m.target, self._size - 1)};
      """

    with self.method(self.element.view_type, ("back", "view"), {"target": self},
      references=(self.view,),
      brief="Get a constant view of the back element",
      description="""
        Returns a constant view of the last element in the array without copying it.

        @param[in] target the array to read from
        @return a constant view of the last element
      """) as m:
      m.inline_code = f"""
        assert(target);
        return {self.view(m.target, self._size - 1)};
      """

    with self.method(Indirection(self.element), "data", {"target": inout(self)}, brief="Get pointer to the underlying array",
      description="""
        Returns a pointer to the contiguous array storage.

        @param[in,out] target the array to inspect
        @return a pointer to the first element
      """) as m:
      m.inline_code = f"""
        assert(target);
        return target->elements;
      """


#
class Range(_Range, DirectAccess):

  brief = "Direct access range over array"

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

    with self.method(Callable.Parameter(self), "new", {"iterable": self.iterable}, brief="Create range spanning the array",
      description="""
        Creates a range over the array elements. The range must not outlive the array.

        @param[in] iterable the array to span
        @return the range covering the whole array
      """) as m:
      result = m.result.variable("result")
      m.inline_code = f"""
        {result.definition};
        assert(iterable);
        result.iterable = iterable;
        result.front = 0;
        result.back = {self.iterable._size};
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
