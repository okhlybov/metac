import metac.std as std
from metac.container import Container, _Range
from metac.range import DirectAccess
from metac.bisectable import Bisectable
from metac.ordered import Ordered
from metac.core import inout, _StructRenderer, Indirection, Callable


#
class Set(_StructRenderer, Bisectable, Ordered, Container):

  def __init__(self, name, element, *args, dependencies=(), **kwargs):
    super().__init__(name, element, *args, dependencies=(*dependencies, std.size_t), **kwargs)
    self.range = Range(self)

  def _element(self, target, index):
    return self.element.variable(f"{target}->elements[{index}]")

  def _target_size(self, target):
    return f"{target}->size"

  @property
  def orderable(self):
    return True

  @property
  def copyable(self):
    return self.element.copyable and self.element.comparable

  def _insert_at_code(self, pos_code, pos_var, element_arg):
    return f"""
      {pos_code}
      if(target->size == target->capacity) {{
        size_t new_capacity = target->capacity == 0 ? 8 : target->capacity * 2;
        {Indirection(self.element)} new_elements = {self.memory.allocate(self.element, "new_capacity")};
        for(i = 0; i < {pos_var}; ++i) {{
          {self.element.move(self.element.variable("new_elements[i]"), self.element.variable("target->elements[i]"))};
        }}
        {self.element.copy(self.element.variable(f"new_elements[{pos_var}]"), element_arg)};
        for(i = {pos_var}; i < target->size; ++i) {{
          {self.element.move(self.element.variable("new_elements[i + 1]"), self.element.variable("target->elements[i]"))};
        }}
        if(target->elements) {{
          {self.memory.free("target->elements")};
        }}
        target->elements = new_elements;
        target->capacity = new_capacity;
      }} else {{
        for(i = target->size; i > {pos_var}; --i) {{
          {self.element.move(self.element.variable("target->elements[i]"), self.element.variable("target->elements[i - 1]"))};
        }}

        {self.element.copy(self.element.variable(f"target->elements[{pos_var}]"), element_arg)};
      }}
      ++target->size;
      return 1;
    """

  def _move_at_code(self, pos_code, pos_var, element_arg):
    return f"""
      {pos_code}
      if(target->size == target->capacity) {{
        size_t new_capacity = target->capacity == 0 ? 8 : target->capacity * 2;
        {Indirection(self.element)} new_elements = {self.memory.allocate(self.element, "new_capacity")};
        for(i = 0; i < {pos_var}; ++i) {{
          {self.element.move(self.element.variable("new_elements[i]"), self.element.variable("target->elements[i]"))};
        }}
        {self.element.move(self.element.variable(f"new_elements[{pos_var}]"), element_arg)};
        for(i = {pos_var}; i < target->size; ++i) {{
          {self.element.move(self.element.variable("new_elements[i + 1]"), self.element.variable("target->elements[i]"))};
        }}
        if(target->elements) {{
          {self.memory.free("target->elements")};
        }}
        target->elements = new_elements;
        target->capacity = new_capacity;
      }} else {{
        for(i = target->size; i > {pos_var}; --i) {{
          {self.element.move(self.element.variable("target->elements[i]"), self.element.variable("target->elements[i - 1]"))};
        }}

        {self.element.move(self.element.variable(f"target->elements[{pos_var}]"), element_arg)};
      }}
      ++target->size;
      return 1;
    """

  def __setup__(self):
    super().__setup__()

    destroy_i = f"{self.element.destroy(self.element.variable('target->elements[i]'))};" if self.element.destructible else ""
    destroy_low = f"{self.element.destroy(self.element.variable('target->elements[low]'))};" if self.element.destructible else ""
    state = self.hasher.state_t.variable("state")

    with self.size as m:
      m.inline_code = """
        assert(target);
        return target->size;
      """

    with self.empty as m:
      m.inline_code = """
        assert(target);
        return target->size == 0;
      """

    with self.create as m:
      m.inline_code = """
        assert(target);
        target->elements = NULL;
        target->size = 0;
        target->capacity = 0;
      """

    with self.method(std.size_t, "capacity", {"target": self}, brief="Get the current allocated capacity",
      description="""
        Returns the number of elements the container can hold without reallocating storage.

        @param[in] target the container to query
        @return the current capacity
      """) as m:
      m.inline_code = """
        assert(target);
        return target->capacity;
      """

    with self.method(Indirection(self.element), "data", {"target": inout(self)}, brief="Get pointer to the contiguous element buffer",
      description="""
        Returns a pointer to the contiguous element buffer. The pointer remains valid
        until the container is modified or destroyed.

        @param[in,out] target the container to query
        @return pointer to the first element
      """) as m:
      m.inline_code = """
        assert(target);
        return target->elements;
      """

    with self.method(None, "reserve", {"target": inout(self), "capacity": std.size_t}, constraint=lambda: self.element.copyable and self.element.comparable, brief="Reserve storage capacity",
      description="""
        Ensures the container has allocated storage for at least the given number of elements.

        @param[in,out] target the container to expand
        @param[in] capacity the minimum capacity to reserve
      """) as m:
      m.code = f"""
        assert(target);
        if({m.capacity} > target->capacity) {{
          {Indirection(self.element)} new_elements;
          size_t i;
          new_elements = {self.memory.allocate(self.element, m.capacity)};
          for(i = 0; i < target->size; ++i) {{
            {self.element.move(self.element.variable("new_elements[i]"), self.element.variable("target->elements[i]"))};
          }}
          if(target->elements) {{
            {self.memory.free("target->elements")};
          }}
          target->elements = new_elements;
          target->capacity = {m.capacity};
        }}
      """

    with self.method(None, "compact", {"target": inout(self)}, constraint=lambda: self.element.copyable and self.element.comparable, brief="Compact buffer capacity to fit element count",
      description="""
        Reduces the allocated capacity down to the current size.

        @param[in,out] target the container to compact
      """) as m:
      m.code = f"""
        assert(target);
        if(target->size == 0) {{
          if(target->elements) {{
            {self.memory.free("target->elements")};
            target->elements = NULL;
          }}
          target->capacity = 0;
        }} else if(target->size < target->capacity) {{
          {Indirection(self.element)} new_elements;
          size_t i;
          new_elements = {self.memory.allocate(self.element, "target->size")};
          for(i = 0; i < target->size; ++i) {{
            {self.element.move(self.element.variable("new_elements[i]"), self.element.variable("target->elements[i]"))};
          }}
          {self.memory.free("target->elements")};
          target->elements = new_elements;
          target->capacity = target->size;
        }}
      """

    with self.destroy as m:
      destroy_loop = f"""
        size_t i;
        for(i = 0; i < target->size; ++i) {{
          {self.element.destroy(self.element.variable("target->elements[i]"))};
        }}
      """ if self.element.destructible else ""
      m.code = f"""
        assert(target);
        if(target->elements) {{
          {destroy_loop}
          {self.memory.free("target->elements")};
        }}
      """

    with self.find_view as m:
      m.references.add(self.lower_bound)
      m.code = f"""
        size_t low;
        assert(target);
        low = {self.lower_bound(m.target, m.element)};
        if(low < target->size && !{self.element.compare(self._element(m.target, "low"), m.element)}) {{
          return {self.element.variable("target->elements[low]").bind(m.result)};
        }}
        return ({self.element.view_type})NULL;
      """

    with self.remove as m:
      m.references.add(self.lower_bound)
      m.code = f"""
        size_t low, i;
        assert(target);
        low = {self.lower_bound(m.target, m.element)};
        if(low < target->size && !{self.element.compare(self._element(m.target, "low"), m.element)}) {{
          {destroy_low}
          for(i = low; i + 1 < target->size; ++i) {{
            {self.element.move(self.element.variable("target->elements[i]"), self.element.variable("target->elements[i + 1]"))};
          }}
          --target->size;
          return 1;
        }}
        return 0;
      """

    with self.method(std.size_t, "count", {"target": self, "element": self.element}, references=(self.lower_bound, self.upper_bound), brief="Count elements equal to given element",
      description="""
        Returns the number of elements in the container equal to the given element in O(log n).

        @param[in] target the container to query
        @param[in] element the element to count
        @return number of equal elements
      """) as m:
      m.code = f"""
        assert(target);
        return {self.upper_bound(m.target, m.element)} - {self.lower_bound(m.target, m.element)};
      """

    with self.method(Callable.Parameter(self.range), ("equal", "range"), {"target": self, "element": self.element}, references=(self.lower_bound, self.upper_bound), brief="Get range covering all elements equal to given element",
      description="""
        Binary searches the container in O(log n) returning the range of elements equal to the given element.
        If no equal elements exist, an empty range is returned.

        @param[in] target the container to search
        @param[in] element the element to search for
        @return the range spanning all matching elements
      """) as m:
      result = m.result.variable("result")
      m.code = f"""
        {result.definition};
        assert(target);
        result.iterable = target;
        result.front = {self.lower_bound(m.target, m.element)};
        result.back = {self.upper_bound(m.target, m.element)};
        return {result};
      """

    with self.copy as m:
      m.code = f"""
        size_t i;
        assert(target);
        assert(source);
        if(source->size > 0) {{
          target->elements = {self.memory.allocate(self.element, "source->size")};
          target->size = source->size;
          target->capacity = source->size;
          for(i = 0; i < source->size; ++i) {{
            {self.element.copy(self.element.variable("target->elements[i]"), self.element.variable("source->elements[i]"))};
          }}
        }} else {{
          target->elements = NULL;
          target->size = 0;
          target->capacity = 0;
        }}
      """

    with self.move as m:
      m.code = """
        assert(target);
        assert(source);
        target->elements = source->elements;
        target->size = source->size;
        target->capacity = source->capacity;
        source->elements = NULL;
        source->size = 0;
        source->capacity = 0;
      """

    with self.equal as m:
      m.code = f"""
        size_t i;
        assert(left);
        assert(right);
        if(left->size != right->size) return 0;
        for(i = 0; i < left->size; ++i) {{
          if(!{self.element.equal(self.element.variable("left->elements[i]"), self.element.variable("right->elements[i]"))})
            return 0;
        }}
        return 1;
      """

    with self.compare as m:
      m.code = f"""
        size_t i, min_size;
        int cmp;
        assert(left);
        assert(right);
        min_size = left->size < right->size ? left->size : right->size;
        for(i = 0; i < min_size; ++i) {{
          cmp = {self.element.compare(self.element.variable("left->elements[i]"), self.element.variable("right->elements[i]"))};
          if(cmp != 0) return cmp;
        }}
        return left->size < right->size ? -1 : (left->size > right->size ? 1 : 0);
      """

    with self.hash as m:
      m.code = f"""
        size_t result;
        size_t i;
        {state.definition};
        assert(target);
        {self.hasher.create(state)};
        for(i = 0; i < target->size; ++i) {{
          {self.hasher.update(state, self.element.hash(self.element.variable("target->elements[i]")))};
        }}
        result = {self.hasher.hash(state)};
        {self.hasher.destroy(state)};
        return result;
      """

  def _render_struct(self, stream, header):
    super()._render_struct(stream, header)
    stream.append(f"""
      struct {self.name} {{
        {Indirection(self.element)} elements; /**< @private */
        size_t size; /**< @private */
        size_t capacity; /**< @private */
      }};
    """)


#
class Range(_Range, DirectAccess):

  def _render_struct(self, stream, header):
    super()._render_struct(stream, header)
    stream.append(f"""
      struct {self.name} {{
        {Indirection(self.iterable, constant=True)} iterable; /**< @private */
        size_t front, /**< @private */ back; /**< @private */
      }};
    """)

  def __setup__(self):
    super().__setup__()

    with self.method(Callable.Parameter(self), "new", {"iterable": self.iterable}, brief="Create the range spanning the whole flat container",
      description="""
        Creates the range covering all elements of the container in ascending order.
        The range must not outlive the container and the container must not be modified while the range is traversed.

        @param[in] iterable the container to span
        @return the range covering the whole container
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
      m.inline_code = """
        assert(target);
        return target->front >= target->back;
      """

    with self.front as m:
      result = m.result.variable("result")
      m.inline_code = f"""
        {result.definition};
        assert(target);
        assert(!{self.empty(m.target)});
        {self.element.copy(result, self.element.variable("target->iterable->elements[target->front]"))};
        return {result};
      """

    with self.front_view as m:
      m.inline_code = f"""
        assert(target);
        assert(!{self.empty(m.target)});
        return {self.element.variable("target->iterable->elements[target->front]").bind(m.result)};
      """

    with self.move_front as m:
      m.inline_code = f"""
        assert(target);
        assert(!{self.empty(m.target)});
        ++target->front;
      """

    with self.back as m:
      result = m.result.variable("result")
      m.inline_code = f"""
        {result.definition};
        assert(target);
        assert(!{self.empty(m.target)});
        {self.element.copy(result, self.element.variable("target->iterable->elements[target->back - 1]"))};
        return {result};
      """

    with self.back_view as m:
      m.inline_code = f"""
        assert(target);
        assert(!{self.empty(m.target)});
        return {self.element.variable("target->iterable->elements[target->back - 1]").bind(m.result)};
      """

    with self.move_back as m:
      m.inline_code = f"""
        assert(target);
        assert(!{self.empty(m.target)});
        --target->back;
      """

    with self.get as m:
      result = m.result.variable("result")
      m.inline_code = f"""
        {result.definition};
        assert(target);
        assert(target->front + {m.index} < target->back);
        {self.element.copy(result, self.element.variable(f"target->iterable->elements[target->front + {m.index}]"))};
        return {result};
      """

    with self.view as m:
      m.inline_code = f"""
        assert(target);
        assert(target->front + {m.index} < target->back);
        return {self.element.variable(f"target->iterable->elements[target->front + {m.index}]").bind(m.result)};
      """

    with self.size as m:
      m.inline_code = """
        assert(target);
        return target->back > target->front ? target->back - target->front : 0;
      """
