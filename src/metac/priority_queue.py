import metac.std as std
from metac.insertable import Insertable
from metac.core import inout, out, Indirection, _StructRenderer, enforced, Orderable, Coerce


#
class Queue(_StructRenderer, Insertable):
  # The extraction-ordered container: the elements are consumed in the priority order -
  # top returns the greatest element per the element comparison. The binary heap over the
  # flat array gives the guaranteed O(log n) push/pop with the contiguous cache friendly
  # storage while handling the duplicate priorities naturally. The heap shape is internal:
  # the iteration is not exposed and the equality and the hashing are not defined
  # (two heaps holding the same elements are not required to have the same shape)

  brief = "Priority queue of elements ordered by priority"

  @enforced
  def __init__(self, name: str, element: Coerce[Orderable], **kwargs):
    super().__init__(name, element, **kwargs)
    self._element_p = Indirection(self.element)

  # The heap shape is internal: two heaps holding the same elements are not required to
  # have the same shape, so the value-ordering operations constrain off via the traits
  @property
  def comparable(self):
    return False

  @property
  def orderable(self):
    return False

  @property
  def hashable(self):
    return False

  def __setup__(self):
    super().__setup__()

    self.description = f"""
      Requires the element type (@ref {self.element}) to be *Orderable*.
      The iteration is not exposed - the elements are consumed one by one via `pop` which
      always yields the greatest element per the element comparison. Duplicate priorities allowed.

      Implemented as the binary heap over the flat array.
      The closest C++ equivalent is [std::priority_queue<>](https://cppreference.com/cpp/container/priority_queue).
    """

    slot0 = self.element.variable("target->elements[0]")
    slot_size = self.element.variable("target->elements[target->size]")

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

    with self.create as m:
      m.inline_code = f"""
        assert(target);
        target->elements = NULL;
        target->capacity = target->size = 0;
      """

    with self.method(None, ("create", "capacity"), {"target": out(self), "capacity": std.size_t}, brief="Create the queue with room for the given number of elements",
      description="""
        Creates the queue with the buffer preallocated for the given number of elements -
        no reallocation takes place until the queue grows past it.

        @param[out] target the queue to construct
        @param[in] capacity the number of elements to reserve room for
      """) as m:
      m.code = f"""
        assert(target);
        if({m.capacity} > 0) {{
          target->elements = {self.memory.allocate(self.element, m.capacity)};
        }} else target->elements = NULL;
        target->capacity = {m.capacity};
        target->size = 0;
      """

    with self.destroy as m:
      if self.element.destructible:
        m.code = f"""
          size_t index;
          assert(target);
          if(target->elements) {{
            for(index = 0; index < target->size; ++index) {self.element.destroy(self.element.variable("target->elements[index]"))};
            {self.memory.free("target->elements")};
          }}
        """
      else:
        m.inline_code = f"""
          assert(target);
          if(target->elements) {self.memory.free("target->elements")};
        """

    with self.copy as m:
      m.code = f"""
        size_t index;
        assert(target);
        assert(source);
        target->elements = {self.memory.allocate(self.element, "source->capacity")};
        target->capacity = source->capacity;
        target->size = source->size;
        for(index = 0; index < source->size; ++index) {self.element.copy(self.element.variable("target->elements[index]"), self.element.variable("source->elements[index]"))};
      """

    with self.move as m:
      m.code = f"""
        assert(target);
        assert(source);
        target->elements = source->elements;
        target->capacity = source->capacity;
        target->size = source->size;
        {self.create(m.source)};
      """

    with self.find_view as m:
      m.code = lambda m: f"""
        size_t index;
        assert(target);
        for(index = 0; index < target->size; ++index) {{
          if({self.element.equal(self.element.variable("target->elements[index]"), m.element)}) {{
            return {self.element.variable("target->elements[index]").bind(m.result)};
          }}
        }}
        return ({self.element.view_type})NULL;
      """

    with self.method(None, "_grow", {"target": inout(self)}, hidden=True, visibility="internal", brief="Grow internal buffer if needed (internal)") as m:
      m.code = f"""
        size_t index, new_capacity;
        {self._element_p} elements;
        assert(target);
        new_capacity = target->capacity ? target->capacity*2 : 8;
        elements = {self.memory.allocate(self.element, "new_capacity")};
        for(index = 0; index < target->size; ++index) {self.element.copy(self.element.variable("elements[index]"), self.element.variable("target->elements[index]"))};
        {self.memory.free("target->elements")};
        target->elements = elements;
        target->capacity = new_capacity;
      """

    with self.method(None, ("sift", "up"), {"target": inout(self), "index": std.size_t}, hidden=True, visibility="internal", brief="Sift element up in heap (internal)") as m:
      m.code = lambda m: f"""
        size_t parent;
        assert(target);
        while({m.index}) {{
          parent = ({m.index} - 1)/2;
          if({self.element.compare(self.element.variable("target->elements[parent]"), self.element.variable(f"target->elements[{m.index}]"))} >= 0) break;
          {self.element.swap(self.element.variable("target->elements[parent]"), self.element.variable(f"target->elements[{m.index}]"))};
          {m.index} = parent;
        }}
      """

    with self.method(None, ("sift", "down"), {"target": inout(self), "index": std.size_t}, hidden=True, visibility="internal", brief="Sift element down in heap (internal)") as m:
      m.code = lambda m: f"""
        size_t child;
        assert(target);
        for(;;) {{
          child = 2*{m.index} + 1;
          if(child >= target->size) break;
          if(child + 1 < target->size && {self.element.compare(self.element.variable("target->elements[child+1]"), self.element.variable("target->elements[child]"))} > 0) ++child;
          if({self.element.compare(self.element.variable(f"target->elements[{m.index}]"), self.element.variable("target->elements[child]"))} >= 0) break;
          {self.element.swap(self.element.variable(f"target->elements[{m.index}]"), self.element.variable("target->elements[child]"))};
          {m.index} = child;
        }}
      """

    with self.method(None, "push", {"target": inout(self), "element": self.element}, constraint=lambda: self.element.copyable and self.element.orderable, brief="Add element to priority queue",
      description="""
        Adds the element to the heap restoring the heap invariant with the O(log n) sift-up.
        The buffer is grown by doubling with element migration when the capacity is exhausted.

        @param[in,out] target the queue to add to
        @param[in] element the element to add
      """) as m:
      m.code = lambda m: f"""
        assert(target);
        if(target->size == target->capacity) {self._grow(m.target)};
        {self.element.copy(slot_size, m.element)};
        ++target->size;
        {self.sift_up(m.target, "target->size - 1")};
      """

    with self.method(None, "emplace", {"target": inout(self)} | self.element.constructor_parameters,
      constraint=lambda: self.element.emplaceable and self.element.orderable and (self.element.copyable or self.element.moveable),
      brief="Construct element in-place and sift up in priority queue",
      description="""
        Constructs an element in-place with forwarded parameters at the leaf and
        restores the heap invariant with the O(log n) sift-up.

        @param[in,out] target the priority queue to add to
      """) as m:
      create_args = [getattr(m, name) for name in self.element.constructor_parameters]
      m.code = lambda m: f"""
        assert(target);
        if(target->size == target->capacity) {self._grow(m.target)};
        {self.element.create(slot_size, *create_args)};
        ++target->size;
        {self.sift_up(m.target, "target->size - 1")};
      """

    with self.method(self.element, "pop", {"target": inout(self)}, constraint=lambda: self.element.moveable and self.element.orderable, brief="Remove and return highest priority element",
      description="""
        Removes and moves out the greatest element per the element comparison in O(log n) -
        the last element replaces the root which is sifted down to restore the heap invariant.
        The returned element is a moved copy so the caller owns it.

        @param[in,out] target the queue to remove from - must not be empty
        @return the highest priority element
      """) as m:
      result = m.result.variable("result")
      m.code = lambda m: f"""
        {result.definition};
        assert(target);
        assert(!{self.empty(m.target)});
        --target->size;
        {self.element.move(result, slot0)};
        if(target->size) {{
          {self.element.move(slot0, slot_size)};
          {self.sift_down(m.target, 0)};
        }}
        return {result};
      """

    with self.put as m:
      m.inline_code = f"""
        assert(target);
        {self.push(m.target, m.element)};
        return 1;
      """

    with self.remove as m:
      destroy_slot_idx = f"{self.element.destroy(self.element.variable('target->elements[index]'))};" if self.element.destructible else ""
      m.code = lambda m: f"""
        size_t index;
        assert(target);
        for(index = 0; index < target->size; ++index) {{
          if({self.element.equal(self.element.variable("target->elements[index]"), m.element)}) {{
            {destroy_slot_idx}
            --target->size;
            if(index < target->size) {{
              {self.element.move(self.element.variable("target->elements[index]"), slot_size)};
              {self.sift_down(m.target, "index")};
              {self.sift_up(m.target, "index")};
            }}
            return 1;
          }}
        }}
        return 0;
      """

    with self.method(self.element, "top", {"target": self}, constraint=lambda: self.element.copyable and self.element.orderable, brief="Get highest priority element",
      description="""
        Returns a copy of the greatest element per the element comparison in O(1) - the
        heap root is always at position 0 without modifying the heap.

        @param[in] target the queue to read - must not be empty
        @return the highest priority element without removing it
      """) as m:
      result = m.result.variable("result")
      m.code = f"""
        {result.definition};
        assert(target);
        assert(!{self.empty(m.target)});
        {self.element.copy(result, slot0)};
        return {result};
      """

    with self.method(self.element.view_type, ("top", "view"), {"target": self}, constraint=lambda: self.element.orderable, brief="Get view of highest priority element",
      description="""
        Returns a pointer to the greatest element per the element comparison in O(1)
        without copying it. The view is valid until the next `push` or `pop` since
        the sift operations may move the element within the buffer.

        @param[in] target the queue to read - must not be empty
        @return a constant view of the highest priority element
      """) as m:
      m.code = f"""
        assert(target);
        assert(!{self.empty(m.target)});
        return {slot0.bind(m.result)};
      """

  def _render_struct(self, stream, header):
    super()._render_struct(stream, header)
    stream.append(f"""
      struct {self.name} {{
        {self._element_p} elements; /**< @private */
        {std.size_t} capacity; /**< @private */
        {std.size_t} size; /**< @private */
      }};
    """)
