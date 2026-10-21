import metac.std as std
from metac.assignable import Assignable
from metac.sortable import Sortable
from metac.sequential import Sequential
from metac.insertable import Insertable
from metac.range import DirectAccess
from metac.container import _Range
from metac.core import out, inout, Callable, Indirection, Macro, _StructRenderer


# Common base class for circular ring buffer containers
class _CircularBuffer(_StructRenderer, Assignable, Sortable, Sequential, Insertable):

  brief = "Ring buffer container with bounded capacity and overwrite semantics"

  def __init__(self, name, element, *args, index=std.size_t, sorting_operations=True, dependencies=(), **kwargs):
    super().__init__(name, element, index, *args, sorting_operations=sorting_operations, dependencies=(*dependencies, std.assert_h, std.string_h), **kwargs)
    self.range = Range(self)

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

  def _capacity(self, target):
    raise NotImplementedError

  # Sortable/Bisectable protocol handlers - the ring maps the logical index onto
  # the physical slot through the modulo of the head offset
  def _element(self, target, index):
    return self.element.variable(f"{target}->elements[({target}->head + ({index})) % {self._capacity(target)}]")

  def _target_size(self, target):
    return f"{target}->size"

  def __setup__(self):
    super().__setup__()

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

    with self.method(self.index, "capacity", {"target": self}, brief="Get the maximum capacity of the circular buffer",
      description="""
        Returns the maximum number of elements the circular buffer can hold before overwriting starts.

        @param[in] target the circular buffer to query
        @return the maximum capacity
      """) as m:
      m.inline_code = f"""
        assert(target);
        return {self._capacity("target")};
      """

    with self.method("int", "full", {"target": self}, brief="Check if the circular buffer is full",
      description="""
        Checks whether the number of elements in the circular buffer has reached its capacity.

        @param[in] target the circular buffer to query
        @return non-zero if the circular buffer is full, zero otherwise
      """) as m:
      m.inline_code = f"""
        assert(target);
        return target->size == {self._capacity("target")};
      """

    with self.indexed as m:
      m.inline_code = f"""
        assert(target);
        return {m.index} < target->size;
      """

    with self.get as m:
      result = m.result.variable("result")
      slot = self.element.variable(f"target->elements[(target->head + ({m.index})) % {self._capacity('target')}]")
      m.inline_code = lambda m: f"""
        {result.definition};
        assert(target);
        assert({self.indexed(m.target, m.index)});
        {self.element.copy(result, slot)};
        return {result};
      """

    with self.view as m:
      slot = self.element.variable(f"target->elements[(target->head + ({m.index})) % {self._capacity('target')}]")
      m.inline_code = f"""
        assert(target);
        assert({self.indexed(m.target, m.index)});
        return {slot.bind(m.result)};
      """

    with self.set as m:
      slot = self.element.variable(f"target->elements[(target->head + ({m.index})) % {self._capacity('target')}]")
      destroy_slot = f"{self.element.destroy(slot)};" if self.element.destructible else ""
      m.inline_code = lambda m: f"""
        assert(target);
        assert({self.indexed(m.target, m.index)});
        {destroy_slot}
        {self.element.copy(slot, m.element)};
      """

    with self.method(self.element, "front", {"target": self}, constraint=lambda: self.element.copyable,
      references=(self.get,),
      brief="Get front element",
      description="""
        Returns a copy of the oldest element at the front in O(1).
        The circular buffer must not be empty.

        @param[in] target the circular buffer to read from - must not be empty
        @return copy of the front element
      """) as m:
      m.inline_code = lambda m: f"""
        assert(target);
        assert(!{self.empty(m.target)});
        return {self.get(m.target, 0)};
      """

    with self.method(self.element.view_type, ("front", "view"), {"target": self},
      references=(self.view,),
      brief="Get constant view of front element",
      description="""
        Returns a constant pointer to the oldest element at the front in O(1) without copying it.
        The circular buffer must not be empty.

        @param[in] target the circular buffer to read from - must not be empty
        @return constant view of the front element
      """) as m:
      m.inline_code = f"""
        assert(target);
        assert(!{self.empty(m.target)});
        return {self.view(m.target, 0)};
      """

    with self.method(self.element, "back", {"target": self}, constraint=lambda: self.element.copyable,
      references=(self.get,),
      brief="Get back element",
      description="""
        Returns a copy of the newest element at the back in O(1).
        The circular buffer must not be empty.

        @param[in] target the circular buffer to read from - must not be empty
        @return copy of the back element
      """) as m:
      m.inline_code = lambda m: f"""
        assert(target);
        assert(!{self.empty(m.target)});
        return {self.get(m.target, "target->size - 1")};
      """

    with self.method(self.element.view_type, ("back", "view"), {"target": self},
      references=(self.view,),
      brief="Get constant view of back element",
      description="""
        Returns a constant pointer to the newest element at the back in O(1) without copying it.
        The circular buffer must not be empty.

        @param[in] target the circular buffer to read from - must not be empty
        @return constant view of the back element
      """) as m:
      m.inline_code = f"""
        assert(target);
        assert(!{self.empty(m.target)});
        return {self.view(m.target, "target->size - 1")};
      """

    with self.method(None, "push", {"target": inout(self), "element": self.element}, constraint=lambda: self.element.copyable, brief="Append element to back",
      description="""
        Appends the element to the back of the circular buffer in O(1).
        If the buffer is already full, the oldest element at the front is overwritten,
        and the front advances forward.

        @param[in,out] target the circular buffer to append to
        @param[in] element the element to append
      """) as m:
      head_slot = self.element.variable("target->elements[target->head]")
      destroy_head = f"{self.element.destroy(head_slot)};" if self.element.destructible else ""
      new_slot = self.element.variable(f"target->elements[(target->head + target->size) % {self._capacity('target')}]")
      m.code = lambda m: f"""
        assert(target);
        assert({self._capacity("target")} > 0);
        if(target->size == {self._capacity("target")}) {{
          {destroy_head}
          {self.element.copy(head_slot, m.element)};
          target->head = (target->head + 1) % {self._capacity("target")};
        }} else {{
          {self.element.copy(new_slot, m.element)};
          ++target->size;
        }}
      """

    with self.method(None, ("push", "back"), {"target": inout(self), "element": self.element}, constraint=lambda: self.element.copyable,
      references=(self.push,),
      brief="Append element to back",
      description="""
        Appends the element to the back of the circular buffer in O(1) (synonym for push).
        If the buffer is already full, the oldest element at the front is overwritten.

        @param[in,out] target the circular buffer to append to
        @param[in] element the element to append
      """) as m:
      m.inline_code = f"""
        assert(target);
        {self.push(m.target, m.element)};
      """

    with self.method(None, ("push", "front"), {"target": inout(self), "element": self.element}, constraint=lambda: self.element.copyable, brief="Prepend element to front",
      description="""
        Prepends the element to the front of the circular buffer in O(1).
        If the buffer is already full, the newest element at the back is overwritten.

        @param[in,out] target the circular buffer to prepend to
        @param[in] element the element to prepend
      """) as m:
      new_head_slot = self.element.variable("target->elements[new_head]")
      destroy_new_head = f"{self.element.destroy(new_head_slot)};" if self.element.destructible else ""
      m.code = lambda m: f"""
        size_t new_head;
        assert(target);
        assert({self._capacity("target")} > 0);
        new_head = (target->head + {self._capacity("target")} - 1) % {self._capacity("target")};
        if(target->size == {self._capacity("target")}) {{
          {destroy_new_head}
          {self.element.copy(new_head_slot, m.element)};
        }} else {{
          {self.element.copy(new_head_slot, m.element)};
          ++target->size;
        }}
        target->head = new_head;
      """

    with self.method(None, ("emplace", "back"), {"target": inout(self)} | self.element.constructor_parameters,
      constraint=lambda: self.element.emplaceable, brief="Construct element in-place at back",
      description="""
        Constructs the element in-place with forwarded parameters at the back of the circular buffer in O(1).
        If the buffer is already full, the oldest element at the front is overwritten.

        @param[in,out] target the circular buffer to append to
      """) as m:
      create_args = [getattr(m, name) for name in self.element.constructor_parameters]
      head_slot = self.element.variable("target->elements[target->head]")
      destroy_head = f"{self.element.destroy(head_slot)};" if self.element.destructible else ""
      new_slot = self.element.variable(f"target->elements[(target->head + target->size) % {self._capacity('target')}]")
      m.code = f"""
        assert(target);
        assert({self._capacity("target")} > 0);
        if(target->size == {self._capacity("target")}) {{
          {destroy_head}
          {self.element.create(head_slot, *create_args)};
          target->head = (target->head + 1) % {self._capacity("target")};
        }} else {{
          {self.element.create(new_slot, *create_args)};
          ++target->size;
        }}
      """
    self.macro("emplace", None, {"target": inout(self)} | self.element.constructor_parameters, lambda target, *args: self.emplace_back(target, *args),
      constraint=lambda: self.element.emplaceable, brief="Construct element in-place at back (synonym for emplace_back)")

    with self.method(None, ("emplace", "front"), {"target": inout(self)} | self.element.constructor_parameters,
      constraint=lambda: self.element.emplaceable, brief="Construct element in-place at front",
      description="""
        Constructs the element in-place with forwarded parameters at the front of the circular buffer in O(1).
        If the buffer is already full, the newest element at the back is overwritten.

        @param[in,out] target the circular buffer to prepend to
      """) as m:
      create_args = [getattr(m, name) for name in self.element.constructor_parameters]
      new_head_slot = self.element.variable("target->elements[new_head]")
      destroy_new_head = f"{self.element.destroy(new_head_slot)};" if self.element.destructible else ""
      m.code = f"""
        size_t new_head;
        assert(target);
        assert({self._capacity("target")} > 0);
        new_head = (target->head + {self._capacity("target")} - 1) % {self._capacity("target")};
        if(target->size == {self._capacity("target")}) {{
          {destroy_new_head}
          {self.element.create(new_head_slot, *create_args)};
        }} else {{
          {self.element.create(new_head_slot, *create_args)};
          ++target->size;
        }}
        target->head = new_head;
      """

    with self.method(self.element, "pop", {"target": inout(self)}, constraint=lambda: self.element.moveable, brief="Remove and return element from front",
      description="""
        Removes and returns the oldest element from the front of the circular buffer in O(1).
        The circular buffer must not be empty.

        @param[in,out] target the circular buffer to pop from - must not be empty
        @return the removed front element
      """) as m:
      result = m.result.variable("result")
      head_slot = self.element.variable("target->elements[target->head]")
      m.code = f"""
        {result.definition};
        assert(target);
        assert(!{self.empty(m.target)});
        {self.element.move(result, head_slot)};
        target->head = (target->head + 1) % {self._capacity("target")};
        --target->size;
        if(target->size == 0) target->head = 0;
        return {result};
      """

    with self.method(self.element, ("pop", "front"), {"target": inout(self)}, constraint=lambda: self.element.moveable,
      references=(self.pop,),
      brief="Remove and return element from front",
      description="""
        Removes and returns the oldest element from the front of the circular buffer in O(1) (synonym for pop).

        @param[in,out] target the circular buffer to pop from - must not be empty
        @return the removed front element
      """) as m:
      m.inline_code = f"""
        assert(target);
        return {self.pop(m.target)};
      """

    with self.method(self.element, ("pop", "back"), {"target": inout(self)}, constraint=lambda: self.element.moveable, brief="Remove and return element from back",
      description="""
        Removes and returns the newest element from the back of the circular buffer in O(1).
        The circular buffer must not be empty.

        @param[in,out] target the circular buffer to pop from - must not be empty
        @return the removed back element
      """) as m:
      result = m.result.variable("result")
      back_slot = self.element.variable(f"target->elements[back_idx]")
      m.code = f"""
        size_t back_idx;
        {result.definition};
        assert(target);
        assert(!{self.empty(m.target)});
        back_idx = (target->head + target->size - 1) % {self._capacity("target")};
        {self.element.move(result, back_slot)};
        --target->size;
        if(target->size == 0) target->head = 0;
        return {result};
      """

    with self.put as m:
      m.inline_code = f"""
        assert(target);
        {self.push(m.target, m.element)};
        return 1;
      """

    target_idx = lambda idx: f"target->elements[(target->head + {idx}) % {self._capacity('target')}]"
    curr_slot = self.element.variable(target_idx("index"))
    next_slot = self.element.variable(target_idx("index + 1"))
    with self.remove as m:
      def _remove(m):
        dest_curr = f"{self.element.destroy(curr_slot)};" if self.element.destructible else ""
        dest_next = f"{self.element.destroy(next_slot)};" if self.element.destructible else ""
        move_shift = (
          f"{self.element.move(curr_slot, next_slot)};"
          if self.element.moveable else
          f"{self.element.copy(curr_slot, next_slot)}; {dest_next}"
        )
        return f"""
          size_t index;
          assert(target);
          for(index = 0; index < target->size; ++index) {{
            if({self.element.equal(curr_slot, m.element)}) {{
              {dest_curr}
              for(; index + 1 < target->size; ++index) {{
                {move_shift}
              }}
              --target->size;
              if(target->size == 0) target->head = 0;
              return 1;
            }}
          }}
          return 0;
        """
      m.code = _remove

    with self.method(None, "clear", {"target": inout(self)}, brief="Clear all elements from the circular buffer",
      description="""
        Destroys all active elements and resets the circular buffer to empty state.
        The capacity is preserved.

        @param[in,out] target the circular buffer to clear
      """) as m:
      target_i = self.element.variable(f"target->elements[(target->head + index) % {self._capacity('target')}]")
      destroy_elem = f"{self.element.destroy(target_i)};" if self.element.destructible else ""
      m.code = f"""
        size_t index;
        assert(target);
        for(index = 0; index < target->size; ++index) {{
          {destroy_elem}
        }}
        target->head = 0;
        target->size = 0;
      """


# Fixed-capacity stack-allocated circular ring buffer
class Static(_CircularBuffer):

  brief = "Fixed-capacity stack-allocated circular ring buffer"

  def __init__(self, name, element, capacity, *args, **kwargs):
    self._fixed_capacity = int(capacity)
    if self._fixed_capacity < 1:
      raise ValueError(f"Static capacity must be at least 1, got {self._fixed_capacity}")
    super().__init__(name, element, *args, **kwargs)

  @property
  def fixed_capacity(self):
    return self._fixed_capacity

  @property
  def constructible(self):
    return True

  @property
  def destructible(self):
    return self.element.destructible

  def _capacity(self, target):
    return str(self._fixed_capacity)

  def _render_struct(self, stream, header):
    super()._render_struct(stream, header)
    stream.append(f"""
      struct {self.name} {{
        {self.element} elements[{self._fixed_capacity}]; /**< @private */
        size_t head; /**< @private */
        size_t size; /**< @private */
      }};
    """)

  def __setup__(self):
    super().__setup__()

    self.description = f"""
      Fixed-capacity stack-allocated circular ring buffer holding at most {self._fixed_capacity} elements.
      Allocates no dynamic heap memory, storing elements inline in an internal array.
      Requires the element type (@ref {self.element}) to be *Copyable*.
      Supports bidirectional element traversal via the corresponding @ref {self.range} iterator
      as well as direct indexed access to its elements.
      When the buffer reaches its maximum capacity of {self._fixed_capacity}, appending elements
      overwrites the oldest elements.
    """

    with self.create as m:
      m.inline_code = f"""
        assert(target);
        target->head = 0;
        target->size = 0;
      """

    if self.element.destructible:
      with self.destroy as m:
        target_i = self.element.variable(f"target->elements[(target->head + index) % {self._fixed_capacity}]")
        m.code = f"""
          size_t index;
          assert(target);
          for(index = 0; index < target->size; ++index) {{
            {self.element.destroy(target_i)};
          }}
        """

    with self.copy as m:
      target_i = self.element.variable("target->elements[index]")
      source_i = self.element.variable(f"source->elements[(source->head + index) % {self._fixed_capacity}]")
      m.code = lambda m: f"""
        size_t index;
        assert(target);
        assert(source);
        target->head = 0;
        target->size = source->size;
        for(index = 0; index < source->size; ++index) {{
          {self.element.copy(target_i, source_i)};
        }}
      """

    with self.move as m:
      target_i = self.element.variable("target->elements[index]")
      source_i = self.element.variable(f"source->elements[(source->head + index) % {self._fixed_capacity}]")
      destroy_src = f"{self.element.destroy(source_i)};" if self.element.destructible else ""
      m.code = lambda m: f"""
        size_t index;
        assert(target);
        assert(source);
        target->head = 0;
        target->size = source->size;
        for(index = 0; index < source->size; ++index) {{
          {self.element.copy(target_i, source_i)};
          {destroy_src}
        }}
        source->head = 0;
        source->size = 0;
      """

    with self.swap as m:
      left_i = self.element.variable("left->elements[index]")
      right_i = self.element.variable("right->elements[index]")
      m.code = f"""
        size_t index, temp_head, temp_size;
        assert(left);
        assert(right);
        temp_head = left->head; left->head = right->head; right->head = temp_head;
        temp_size = left->size; left->size = right->size; right->size = temp_size;
        for(index = 0; index < {self._fixed_capacity}; ++index) {{
          {self.element.swap(left_i, right_i)};
        }}
      """


# Bounded heap-allocated circular ring buffer with runtime capacity and resizing
class Dynamic(_CircularBuffer):

  brief = "Bounded heap-allocated circular ring buffer with runtime capacity and resizing"

  def __init__(self, name, element, *args, **kwargs):
    super().__init__(name, element, *args, **kwargs)

  @property
  def constructible(self):
    return False

  @property
  def destructible(self):
    return True

  def _capacity(self, target):
    return f"({target}->capacity)"

  def _render_struct(self, stream, header):
    super()._render_struct(stream, header)
    stream.append(f"""
      struct {self.name} {{
        {Indirection(self.element)} elements; /**< @private */
        size_t head; /**< @private */
        size_t size; /**< @private */
        size_t capacity; /**< @private */
      }};
    """)

  def __setup__(self):
    super().__setup__()

    self.description = f"""
      Bounded heap-allocated circular ring buffer with capacity determined at runtime upon creation.
      Requires the element type (@ref {self.element}) to be *Copyable*.
      Supports bidirectional element traversal via the corresponding @ref {self.range} iterator
      as well as direct indexed access to its elements.
      Supports dynamic buffer reallocation via @ref {self.decorate(('set', 'capacity'))}.
      When the buffer reaches its capacity, appending elements overwrites the oldest elements.
    """

    with self.method(None, "create", {"target": out(self), "capacity": std.size_t}, brief="Create the circular buffer with given capacity",
      description="""
        Allocates and initializes the circular buffer on the heap with the specified capacity.

        @param[out] target the circular buffer to construct
        @param[in] capacity maximum number of elements the buffer can hold - must be greater than zero
      """) as m:
      m.code = f"""
        assert(target);
        assert(capacity > 0);
        target->elements = {self.memory.allocate(self.element, "capacity")};
        target->head = 0;
        target->size = 0;
        target->capacity = capacity;
      """

    with self.destroy as m:
      destroy_elements = f"""
        size_t index;
        for(index = 0; index < target->size; ++index) {{
          size_t slot = (target->head + index) % target->capacity;
          {self.element.destroy(self.element.variable("target->elements[slot]"))};
        }}
      """ if self.element.destructible else ""
      m.code = f"""
        assert(target);
        if(target->elements) {{
          {destroy_elements}
          {self.memory.free("target->elements")};
        }}
      """

    with self.copy as m:
      m.code = lambda m: f"""
        size_t index;
        assert(target);
        assert(source);
        assert(source->capacity > 0);
        target->elements = {self.memory.allocate(self.element, "source->capacity")};
        target->head = 0;
        target->size = source->size;
        target->capacity = source->capacity;
        for(index = 0; index < source->size; ++index) {{
          size_t src_slot = (source->head + index) % source->capacity;
          {self.element.copy(self.element.variable("target->elements[index]"), self.element.variable("source->elements[src_slot]"))};
        }}
      """

    with self.move as m:
      m.code = f"""
        assert(target);
        assert(source);
        target->elements = source->elements;
        target->head = source->head;
        target->size = source->size;
        target->capacity = source->capacity;
        source->elements = NULL;
        source->head = 0;
        source->size = 0;
        source->capacity = 0;
      """

    with self.swap as m:
      m.code = f"""
        {Indirection(self.element)} tmp_elements;
        size_t tmp_head, tmp_size, tmp_capacity;
        assert(left);
        assert(right);
        tmp_elements = left->elements;
        tmp_head = left->head;
        tmp_size = left->size;
        tmp_capacity = left->capacity;
        left->elements = right->elements;
        left->head = right->head;
        left->size = right->size;
        left->capacity = right->capacity;
        right->elements = tmp_elements;
        right->head = tmp_head;
        right->size = tmp_size;
        right->capacity = tmp_capacity;
      """

    with self.method(None, ("set", "capacity"), {"target": inout(self), "new_capacity": std.size_t}, constraint=lambda: self.element.copyable, brief="Change buffer capacity",
      description="""
        Reallocates the buffer to the new capacity. If the new capacity is smaller than the current size,
        the oldest elements are discarded so that at most new_capacity elements remain.

        @param[in,out] target the circular buffer to resize
        @param[in] new_capacity the new maximum capacity - must be greater than zero
      """) as m:
      m.code = lambda m: f"""
        assert(target);
        assert(new_capacity > 0);
        if(new_capacity != target->capacity) {{
          {Indirection(self.element)} new_elements;
          size_t index, keep_count, discard_count, old_capacity;
          new_elements = {self.memory.allocate(self.element, "new_capacity")};
          keep_count = target->size < new_capacity ? target->size : new_capacity;
          discard_count = target->size - keep_count;
          old_capacity = target->capacity;
          for(index = 0; index < discard_count; ++index) {{
            size_t old_slot = (target->head + index) % old_capacity;
            {self.element.destroy(self.element.variable("target->elements[old_slot]")) if self.element.destructible else str()};
          }}
          for(index = 0; index < keep_count; ++index) {{
            size_t old_slot = (target->head + discard_count + index) % old_capacity;
            {self.element.copy(self.element.variable("new_elements[index]"), self.element.variable("target->elements[old_slot]"))};
            {self.element.destroy(self.element.variable("target->elements[old_slot]")) if self.element.destructible else str()};
          }}
          if(target->elements) {{
            {self.memory.free("target->elements")};
          }}
          target->elements = new_elements;
          target->head = 0;
          target->size = keep_count;
          target->capacity = new_capacity;
        }}
      """


# Range iterator for circular buffer
class Range(_Range, DirectAccess):

  def _render_struct(self, stream, header):
    super()._render_struct(stream, header)
    stream.append(f"""
      struct {self.name} {{
        {Indirection(self.iterable, constant=True)} iterable; /**< @private */
        {self.iterable.index} front, /**< @private */ back; /**< @private */
      }};
    """)

  def _copy(self, result, parameters, **kwargs):
    return Macro(result, parameters, lambda target, source: f"{target} = {source}", **kwargs)

  def __setup__(self):
    super().__setup__()

    with self.method(Callable.Parameter(self), "new", {"iterable": self.iterable}, brief="Create the range spanning the circular buffer",
      description="""
        Creates the range covering the circular buffer. The range must not outlive
        the circular buffer and the circular buffer must not be modified while the range is traversed.

        @param[in] iterable the circular buffer to span
        @return the range covering the circular buffer
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
