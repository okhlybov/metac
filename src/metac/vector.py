import metac.std as std
from metac.assignable import Assignable
from metac.sortable import Sortable
from metac.sequential import Sequential
from metac.insertable import Insertable
from metac.range import DirectAccess
from metac.container import _Range
from metac.core import out, inout, Macro, Callable, Indirection, _StructRenderer


#
class Vector(_StructRenderer, Assignable, Sortable, Sequential, Insertable):

  brief = "Direct access sequence container"
  
  def __init__(self, name, element, inline_capacity=0, *args, index=std.size_t, sorting_operations=True, dependencies=(), **kwargs):
    self.inline_capacity = int(inline_capacity)
    if self.inline_capacity < 0:
      raise ValueError(f"Vector inline_capacity must be non-negative, got {self.inline_capacity}")
    super().__init__(name, element, index, *args, sorting_operations=sorting_operations, dependencies=(*dependencies, std.string_h), **kwargs)
    self.range = Range(self)

  def _data(self, target):
    if self.inline_capacity > 0:
      return f"({target}->capacity <= {self.inline_capacity} ? {target}->storage.inline_elements : {target}->storage.heap_elements)"
    return f"({target}->elements)"

  def _free_heap(self, target):
    if self.inline_capacity > 0:
      return f"if({target}->capacity > {self.inline_capacity}) {{ {self.memory.free(f'{target}->storage.heap_elements')}; }}"
    return f"if({target}->elements) {{ {self.memory.free(f'{target}->elements')}; }}"

  def _set_heap(self, target, ptr, capacity):
    if self.inline_capacity > 0:
      return f"{target}->storage.heap_elements = {ptr}; {target}->capacity = {capacity};"
    return f"{target}->elements = {ptr}; {target}->capacity = {capacity};"

  def _element(self, target, index):
    return self.element.variable(f"{self._data(target)}[{index}]")

  # Transfers one element into a freshly allocated buffer during a reallocation:
  # the movable elements migrate by the O(1) move (a vector of containers hands
  # over its buffers instead of deep-copying them), the immovable ones by the
  # copy-destroy pair
  def _migrate_element(self, destination, source):
    if self.element.moveable:
      return f"{self.element.move(self.element.variable(destination), source)};"
    destroy_source = f"{self.element.destroy(source)};" if self.element.destructible else ""
    return f"{self.element.copy(self.element.variable(destination), source)}; {destroy_source}"

  def _target_size(self, target):
    return f"{target}->size"

  def __setup__(self):
    super().__setup__()
    
    self.description = f"""
      Requires the element type (@ref {self.element}) to be *DefaultConstructible* and *Copyable*.
      Supports bidirectional element traversal via the corresponding @ref {self.range} iterator as well as subranging with direct indexed access to the subrange's elements.

      Implemented as the contiguous array of elements.
      {"Supports small buffer optimization (SBO) with inline capacity of " + str(self.inline_capacity) + " elements avoiding heap allocations until exceeded." if self.inline_capacity > 0 else "Dynamically allocates contiguous element storage on the heap."}
      The closest C++ equivalent is [std::vector<>](https://cppreference.com/cpp/container/vector).
    """

    data = self._data("target")
    left_i = self.element.variable(f"{self._data('left')}[index]")
    right_i = self.element.variable(f"{self._data('right')}[index]")
    source_i = self.element.variable(f"{self._data('source')}[index]")
    target_i = self.element.variable(f"{data}[index]")

    with self.empty as m:
      m.inline_code = f"""
        assert(target);
        return target->size == 0;
      """
    
    with self.indexed as m:
      m.inline_code = f"""
        assert(target);
        return index < target->size;
      """
    
    with self.size as m:
      m.inline_code = f"""
        assert(target);
        return target->size;
      """

    with self.method(self.index, "capacity", {"target": self}, brief="Get the current allocated capacity",
      description="""
        Returns the number of elements the vector can hold without reallocating storage.

        @param[in] target the vector to query
        @return the current capacity
      """) as m:
      m.inline_code = f"""
        assert(target);
        return target->capacity;
      """

    with self.method(Indirection(self.element), "data", {"target": inout(self)}, brief="Get pointer to the contiguous element buffer",
      description="""
        Returns a pointer to the contiguous element buffer. The pointer remains valid
        until the vector is resized, reallocated by push, or destroyed.

        @param[in,out] target the vector to query
        @return pointer to the first element
      """) as m:
      m.inline_code = f"""
        assert(target);
        return {data};
      """
    
    with self.method(None, "allocate", {"target": out(self), "capacity": self.index}, visibility="private", brief="Allocate the element storage with given capacity (private)") as m:
      if self.inline_capacity > 0:
        m.code = f"""
          assert(target);
          if({m.capacity} > {self.inline_capacity}) {{
            target->storage.heap_elements = {self.memory.allocate(self.element, m.capacity)};
            target->capacity = {m.capacity};
          }} else {{
            target->capacity = {self.inline_capacity};
          }}
          target->size = {m.capacity};
        """
      else:
        m.code = f"""
          assert(target);
          if({m.capacity} > 0) {{
            target->elements = {self.memory.allocate(self.element, m.capacity)};
            target->capacity = {m.capacity};
          }} else {{
            target->elements = NULL;
            target->capacity = 0;
          }}
          target->size = {m.capacity};
        """
    
    # The zero initializable elements are default initialized by the zeroed allocation alone
    with self.method(None, ("create", "size"), {"target": out(self), "size": self.index}, constraint=lambda: self.element.default_constructible or self.element.zero_initializable, brief="Create vector with the given number of default-initialized elements",
      description="""
        Creates the vector holding exactly the given number of default-initialized elements.
        Zero-initializable elements are initialized by the zeroed buffer allocation alone;
        otherwise each element is default constructed in place over the freshly allocated buffer.

        @param[out] target the vector to construct
        @param[in] size the number of default-initialized elements to create
      """) as m:
      if self.element.zero_initializable:
        if self.inline_capacity > 0:
          m.code = f"""
            assert(target);
            if({m.size} > {self.inline_capacity}) {{
              target->storage.heap_elements = {self.memory.allocate(self.element, m.size, zero=True)};
              target->capacity = {m.size};
            }} else {{
              memset(target->storage.inline_elements, 0, {m.size} * sizeof({self.element}));
              target->capacity = {self.inline_capacity};
            }}
            target->size = {m.size};
          """
        else:
          m.code = f"""
            assert(target);
            if({m.size} > 0) {{
              target->elements = {self.memory.allocate(self.element, m.size, zero=True)};
              target->capacity = {m.size};
            }} else {{
              target->elements = NULL;
              target->capacity = 0;
            }}
            target->size = {m.size};
          """
      elif self.element.default_constructible:
        m.code = f"""
          {self.index} index;
          assert(target);
          {self.allocate(*m.arguments)};
          for(index = 0; index < {m.size}; ++index) {self.element.create(target_i)};
        """

    with self.get as m:
      result = m.result.variable("result")
      m.inline_code = lambda m: f"""
        {result.definition};
        assert(target);
        assert({self.indexed(m.target, m.index)});
        {self.element.copy(result, target_i)};
        return {result};
      """
    
    # FIXME explicit casting here and ithere in the respective Range type is a kind of hack to deal with double pointer types
    # Normally Pointer type should be responsible for handling the per-indirection constness flags
    
    with self.view as m:
      m.inline_code = f"""
        assert(target);
        assert({self.indexed(m.target, m.index)});
        return {target_i.bind(m.result)};
      """

    destroy_i = self.element.destroy(target_i) if self.element.destructible else str()
    
    with self.set as m:
      m.inline_code = lambda m: f"""
        assert(target);
        assert({self.indexed(m.target, m.index)});
        {destroy_i};
        {self.element.copy(target_i, m.element)};
      """

    # Resize follows the std::vector::resize semantics: growing default-initializes the
    # new tail elements while shrinking destroys the removed tail. Growing reallocates
    # the exact size buffer and migrates the old elements by copy; shrinking only
    # destroys the tail since the buffer is a single allocation freed as a whole
    with self.method(None, "resize", {"target": inout(self), "size": self.index}, constraint=lambda: self.element.copyable and (self.element.default_constructible or self.element.zero_initializable), brief="Resize the vector to the given number of elements",
      description="""
        Changes the number of elements following the std::vector::resize semantics: growing appends
        default-initialized elements while shrinking destroys the removed tail.
        Growing reallocates the exact size buffer and migrates the old elements by copy, so the
        element pointers into the vector do not survive it; shrinking keeps the allocation and
        only destroys the tail since the buffer is a single allocation freed as a whole.

        @param[in,out] target the vector to resize
        @param[in] size the new number of elements - the tail is destroyed when shrinking and default-initialized when growing
      """) as m:
      if self.element.zero_initializable:
        def _resize_zero(m):
          migrate = self._migrate_element("elements[index]", target_i)
          return f"""
            {self.index} index;
            assert(target);
            if({m.size} > target->size) {{
              if({m.size} > target->capacity) {{
                {Indirection(self.element)} elements;
                elements = {self.memory.allocate(self.element, m.size, zero=True)};
                for(index = 0; index < target->size; ++index) {{
                  {migrate}
                }}
                {self._free_heap("target")}
                {self._set_heap("target", "elements", m.size)}
              }} else {{
                memset(&({data}[target->size]), 0, ({m.size} - target->size) * sizeof({self.element}));
              }}
            }} else {{
              for(index = {m.size}; index < target->size; ++index) {{
                {destroy_i};
              }}
            }}
            target->size = {m.size};
          """
        m.code = _resize_zero
      elif self.element.default_constructible:
        def _resize_construct(m):
          migrate = self._migrate_element("elements[index]", target_i)
          return f"""
            {self.index} index;
            assert(target);
            if({m.size} > target->size) {{
              if({m.size} > target->capacity) {{
                {Indirection(self.element)} elements;
                elements = {self.memory.allocate(self.element, m.size)};
                for(index = 0; index < target->size; ++index) {{
                  {migrate}
                }}
                {self._free_heap("target")}
                {self._set_heap("target", "elements", m.size)}
              }}
              for(index = target->size; index < {m.size}; ++index) {{
                {self.element.create(target_i)};
              }}
            }} else {{
              for(index = {m.size}; index < target->size; ++index) {{
                {destroy_i};
              }}
            }}
            target->size = {m.size};
          """
        m.code = _resize_construct

    with self.method(None, "push", {"target": inout(self), "element": self.element}, constraint=lambda: self.element.copyable, brief="Add element to back",
      description="""
        Appends the element to the back in amortized O(1), reallocating the buffer with geometric
        doubling when the capacity is exhausted.

        @param[in,out] target the vector to add to
        @param[in] element the element to add to the back
      """) as m:
      def _push(m):
        migrate = self._migrate_element("elements[index]", target_i)
        return f"""
          assert(target);
          if(target->size == target->capacity) {{
            {self.index} index, new_capacity;
            {Indirection(self.element)} elements;
            new_capacity = target->capacity == 0 ? 8 : target->capacity * 2;
            elements = {self.memory.allocate(self.element, "new_capacity")};
            for(index = 0; index < target->size; ++index) {{
              {migrate}
            }}
            {self._free_heap("target")}
            {self._set_heap("target", "elements", "new_capacity")}
          }}
          {self.element.copy(self.element.variable(f"{data}[target->size]"), m.element)};
          ++target->size;
        """
      m.code = _push

    with self.method(None, ("emplace", "back"), {"target": inout(self)} | self.element.constructor_parameters,
      constraint=lambda: self.element.emplaceable and (self.element.copyable or self.element.moveable), brief="Construct element in-place at back",
      description="""
        Appends an element constructed in-place with forwarded parameters to the back
        in amortized O(1), reallocating the buffer with geometric doubling when exhausted.

        @param[in,out] target the vector to add to
      """) as m:
      def _emplace_back(m):
        create_args = [getattr(m, name) for name in self.element.constructor_parameters]
        migrate = self._migrate_element("elements[index]", target_i)
        return f"""
          assert(target);
          if(target->size == target->capacity) {{
            {self.index} index, new_capacity;
            {Indirection(self.element)} elements;
            new_capacity = target->capacity == 0 ? 8 : target->capacity * 2;
            elements = {self.memory.allocate(self.element, "new_capacity")};
            for(index = 0; index < target->size; ++index) {{
              {migrate}
            }}
            {self._free_heap("target")}
            {self._set_heap("target", "elements", "new_capacity")}
          }}
          {self.element.create(self.element.variable(f"{data}[target->size]"), *create_args)};
          ++target->size;
        """
      m.code = _emplace_back
    self.macro("emplace", None, {"target": inout(self)} | self.element.constructor_parameters, lambda target, *args: self.emplace_back(target, *args),
      constraint=lambda: self.element.emplaceable and (self.element.copyable or self.element.moveable), brief="Construct element in-place at back (synonym for emplace_back)")

    with self.method(self.element, "pop", {"target": inout(self)}, constraint=lambda: self.element.moveable, brief="Remove and return element from back",
      description="""
        Removes and returns the back element in O(1). The vector must not be empty.

        @param[in,out] target the vector to remove from - must not be empty
        @return the removed back element
      """) as m:
      result = m.result.variable("result")
      last_i = self.element.variable(f"{data}[target->size]")
      m.code = f"""
        {result.definition};
        assert(target);
        assert(!{self.empty(m.target)});
        --target->size;
        {self.element.move(result, last_i)};
        return {result};
      """

    with self.put as m:
      m.inline_code = f"""
        assert(target);
        {self.push(m.target, m.element)};
        return 1;
      """

    target_next_i = self.element.variable(f"{data}[index + 1]")
    with self.remove as m:
      def _remove(m):
        destroy_next = f"{self.element.destroy(target_next_i)};" if self.element.destructible else ""
        move_shift = (
          f"{self.element.move(target_i, target_next_i)};"
          if self.element.moveable else
          f"{self.element.copy(target_i, target_next_i)}; {destroy_next}"
        )
        return f"""
          {self.index} index;
          assert(target);
          for(index = 0; index < target->size; ++index) {{
            if({self.element.equal(target_i, m.element)}) {{
              {destroy_i};
              for(; index + 1 < target->size; ++index) {{
                {move_shift};
              }}
              --target->size;
              return 1;
            }}
          }}
          return 0;
        """
      m.code = _remove

    with self.method(None, "compact", {"target": inout(self)}, constraint=lambda: self.element.copyable, brief="Compact buffer capacity to fit element count",
      description="""
        Reduces the allocated capacity down to the current size. If the vector has inline capacity
        and the current element count fits within it, dynamic heap memory is freed and the elements
        revert to the inlined buffer.

        @param[in,out] target the vector to compact
      """) as m:
      if self.inline_capacity > 0:
        def _compact_inline(m):
          migrate_heap = self._migrate_element("target->storage.inline_elements[index]", self.element.variable("heap[index]"))
          migrate = self._migrate_element("elements[index]", target_i)
          return f"""
            {self.index} index;
            assert(target);
            if(target->capacity > {self.inline_capacity}) {{
              if(target->size <= {self.inline_capacity}) {{
                {Indirection(self.element)} heap = target->storage.heap_elements;
                for(index = 0; index < target->size; ++index) {{
                  {migrate_heap}
                }}
                {self.memory.free("heap")};
                target->capacity = {self.inline_capacity};
              }} else if(target->size < target->capacity) {{
                {Indirection(self.element)} elements = {self.memory.allocate(self.element, "target->size")};
                for(index = 0; index < target->size; ++index) {{
                  {migrate}
                }}
                {self.memory.free("target->storage.heap_elements")};
                target->storage.heap_elements = elements;
                target->capacity = target->size;
              }}
            }}
          """
        m.code = _compact_inline
      else:
        def _compact(m):
          migrate = self._migrate_element("elements[index]", target_i)
          return f"""
            {self.index} index;
            assert(target);
            if(target->size == 0) {{
              if(target->elements) {{
                {self.memory.free("target->elements")};
                target->elements = NULL;
              }}
              target->capacity = 0;
            }} else if(target->size < target->capacity) {{
              {Indirection(self.element)} elements = {self.memory.allocate(self.element, "target->size")};
              for(index = 0; index < target->size; ++index) {{
                {migrate}
              }}
              {self.memory.free("target->elements")};
              target->elements = elements;
              target->capacity = target->size;
            }}
          """
        m.code = _compact

    with self.create as m:
      if self.inline_capacity > 0:
        m.inline_code = f"""
          assert(target);
          target->size = 0;
          target->capacity = {self.inline_capacity};
        """
      else:
        m.inline_code = """
          assert(target);
          target->elements = NULL;
          target->size = 0;
          target->capacity = 0;
        """
    
    with self.destroy as m:
      destroy_loop = f"""
        {self.index} index;
        if(target->size > 0) {{
          for(index = 0; index < target->size; ++index) {self.element.destroy(target_i)};
        }}
      """ if self.element.destructible else ""
      m.code = f"""
        assert(target);
        {destroy_loop}
        {self._free_heap("target")}
      """

    with self.copy as m:
      m.code = lambda m: f"""
        {self.index} index;
        assert(target);
        assert(source);
        {self.allocate(m.target, "source->size")};
        for(index = 0; index < target->size; ++index) {self.element.copy(target_i, source_i)};
      """

    with self.move as m:
      if self.inline_capacity > 0:
        m.code = f"""
          {self.index} index;
          assert(target);
          assert(source);
          if(source->capacity > {self.inline_capacity}) {{
            target->storage.heap_elements = source->storage.heap_elements;
            target->size = source->size;
            target->capacity = source->capacity;
            {self.create(m.source)};
          }} else {{
            target->size = source->size;
            target->capacity = {self.inline_capacity};
            for(index = 0; index < source->size; ++index) {{
              {self.element.move(target_i, source_i)};
            }}
            {self.create(m.source)};
          }}
        """
      else:
        m.code = f"""
          assert(target);
          assert(source);
          target->elements = source->elements;
          target->size = source->size;
          target->capacity = source->capacity;
          {self.create(m.source)};
        """



  def _render_struct(self, stream, header):
    super()._render_struct(stream, header)
    if self.inline_capacity > 0:
      stream.append(f"""
        struct {self.name} {{
          {self.index} size; /**< @private */
          {self.index} capacity; /**< @private */
          union {{
            {self.element} inline_elements[{self.inline_capacity}]; /**< @private */
            {Indirection(self.element)} heap_elements; /**< @private */
          }} storage; /**< @private */
        }};
      """)
    else:
      stream.append(f"""
        struct {self.name} {{
          {Indirection(self.element)} elements; /**< @private */
          {self.index} size; /**< @private */
          {self.index} capacity; /**< @private */
        }};
      """)


#
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

    with self.method(Callable.Parameter(self), "new", {"iterable" : self.iterable}, brief="Create the range spanning the whole vector",
      description="""
        Creates the range over the contiguous element buffer. The range must not outlive
        the vector and the vector must not be resized while the range is traversed.

        @param[in] iterable the vector to span
        @return the range covering the whole vector
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
      assert(index < target->back - target->front);
      return {self.iterable.get("target->iterable", "target->front + index")};
    """

    with self.view as m:
      m.inline_code = lambda: f"""
        assert(target);
        assert(index < target->back - target->front);
        return {self.iterable.view("target->iterable", "target->front + index")};
      """

    with self.size as m:
      m.inline_code = f"""
        assert(target);
        assert(target->back >= target->front);
        return target->back - target->front;
      """