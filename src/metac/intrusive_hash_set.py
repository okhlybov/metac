import metac.std as std
from metac.range import Forward
import metac.set
from metac.hashed import Hashed
from metac.container import _Range
from metac.core import out, inout, Macro, Indirection, Callable, Composite, _StructRenderer, _ceil_power2
from metac.intrusive_option import Option as IntrusiveOption


#
class Set(_StructRenderer, metac.set.Set, Hashed):

  brief = "Set of distinct elements over open addressing with sentinel values"
  
  def __init__(self, name, element, states, *args, capacity_threshold=0.75, dependencies=(), **kwargs):
    super().__init__(name, element, *args, dependencies=(*dependencies, _ceil_power2), **kwargs)
    self.slot = IntrusiveOption(
      self._decorate_component("slot", abbreviate=True),
      self.element,
      states,
      visibility="internal",
    )
    self.dependencies.add(self.slot)
    self._slot_p = Indirection(self.slot)
    self._element_p = Indirection(self.element)
    self.capacity_threshold = capacity_threshold
    self.range = Range(self)

  @property
  def orderable(self):
    return False

  def __setup__(self):
    super().__setup__()

    self.description = f"""
      Requires the element type (@ref {self.element}) to be *Hashable*, *Comparable* and to reserve
      the two sentinel states - the empty and the deleted slots of the table.
      Supports one way element traversal via the corresponding @ref {self.range} iterator.

      Implemented as the hash table with the flat open addressing over the sentinel carrying elements.
      The closest C++ equivalent is [std::unordered_set<>](https://cppreference.com/cpp/container/unordered_set).
    """

    target_element = self.element.variable("target->elements[index]")
    target_slot = self.slot.variable("target->elements[index]")
    source_element = self.element.variable("source->elements[index]")
    source_slot = self.slot.variable("source->elements[index]")
    target_elements = self._slot_p.variable("target->elements")
    
    with self.size as m:
      m.inline_code = f"""
      assert(target);
      return target->size;
    """

    with self.method("int", ("is", "element"), {"element": self.element}, visibility="internal", hidden=True, brief="Check if the element slot holds a live element (internal)") as m:
      elem_expr = f"(*{m.element})" if isinstance(self.element, Composite) and not isinstance(self.element, Indirection) else m.element
      m.code = f"""
        return {self.slot._engaged(elem_expr)};
      """
    
    with self.method(None, "allocate", {"target": inout(self), "capacity": std.size_t}, hidden=True, visibility="internal", references=(_ceil_power2,),
      brief="Allocate the element table with the capacity rounded up to a power of two (internal)") as m:
      m.code = f"""
        assert(target);
        assert(capacity > 0);
        target->size = 0;
        target->capacity = _metac_ceil_power2(capacity);
        assert(!(target->capacity & (target->capacity - 1))); /* verify the capacity is a power of 2 */
        {target_elements} = {self.memory.allocate(self.slot, "target->capacity")};
      """
    
    _target = self.variable("_target")
    
    with self.create as m:
      m.inline_code = f"""
        assert(target);
        target->elements = NULL;
        target->capacity = target->size = 0;
      """

    with self.method(None, ("create", "capacity"), {"target": out(self), "capacity": std.size_t}, hidden=True, visibility="internal",
      references=(self.allocate, self.create),
      brief="Create set with given capacity (internal)") as m:
      m.code = f"""
        size_t index;
        assert(target);
        if(capacity) {{
          {self.allocate(m.target, m.capacity)};
          for(index = 0; index < target->capacity; ++index) {{{self.slot.create(target_slot)};}}
        }} else {{
          {self.create(m.target)};
        }}
      """

    with self.method(None, ("create", "size"), {"target": out(self), "size": std.size_t},
      references=(self.create_capacity,),
      brief="Create set with estimated element count",
      description="""
        Creates the set preallocating the element table for the estimated element count - the
        table capacity is the given estimate divided by the load factor threshold and rounded
        up to a power of two. No rehashing takes place until the set grows past the estimate.

        @param[out] target the set to construct
        @param[in] size the estimated element count used to preallocate the element table
      """) as m:
      m.code = f"""
        assert(target);
        {self.create_capacity(m.target, f"(size_t)({m.size}/{self.capacity_threshold})")};
      """
    
    with self.method(Callable.Parameter(self._element_p), ("locate", "element"), {"target": self, "_index": out(std.size_t), "element": self.element}, visibility="internal", hidden=True, constraint=lambda: self.element.comparable, brief="Locate element by value (internal)") as m:
      m.code = f"""
        size_t index, start;
        {self._element_p} _element = NULL;
        assert(target);
        assert(_index);
        assert({self.is_element(m.element)});
        /* linear probing */
        if(target->elements) {{
          assert(target->capacity > 0);
          start = {self.element.hash_lookup_hash(m.element)} & (target->capacity-1); /* capacity is assumed to be the power of 2 */
          /* lookup terminator for the existing entry is an empty slot while deleted slot is not */
          for(index = start; index < target->capacity; ++index) {{
            if(!{self.slot.empty(target_slot)}) {{
              if({self.slot.primed(target_slot)} && {self.element.hash_lookup_equal(target_element, m.element)}) {{
                _element = ({self._element_p})&{target_element};
                goto stop;
              }}
            }} else goto stop;
          }}
          for(index = 0; index < start; ++index) {{
            if(!{self.slot.empty(target_slot)}) {{
              if({self.slot.primed(target_slot)} && {self.element.hash_lookup_equal(target_element, m.element)}) {{
                _element = ({self._element_p})&{target_element};
                goto stop;
              }}
            }} else goto stop;
          }}
          stop:
            *_index = index;
            return _element;
        }}
        return NULL;
      """
    
    with self.method(Callable.Parameter(self._element_p), ("locate", "slot"), {"target": self, "_index": out(std.size_t), "element": self.element}, visibility="internal", hidden=True, constraint=lambda: self.element.comparable, brief="Locate empty slot for element (internal)") as m:
      m.code = f"""
        size_t index, start;
        assert(target);
        assert(_index);
        assert(target->capacity > 0);
        assert(target->size < target->capacity);
        assert({self.is_element(m.element)});
        /* linear probing */
        start = {self.element.hash_lookup_hash(m.element)} & (target->capacity-1); /* capacity is assumed to be the power of 2 */
        /* lookup terminator for non-existing entry is either empty or deleted slot */
        for(index = start; index < target->capacity; ++index) {{
          if(!{self.slot.primed(target_slot)}) {{
            *_index = index;
            return ({self._element_p})&{target_element};
          }}
        }}
        for(index = 0; index < start; ++index) {{
          if(!{self.slot.primed(target_slot)}) {{
            *_index = index;
            return ({self._element_p})&{target_element};
          }}
        }}
        abort(); /* not finding a suitable empty slot is a fatal error */
      """

    with self.method(None, "resize", {"target": inout(self), "new_size": std.size_t}, hidden=True, constraint=lambda: self.element.copyable, references=(_ceil_power2,), brief="Resize hash table (internal)") as m:
      m.code = f"""
        {_target.definition};
        size_t index, _index, new_capacity;
        assert(target);
        new_capacity = _metac_ceil_power2((size_t)(new_size/{self.capacity_threshold})); /* predict new capacity after size changing respecting the desired capacity threshold */
        if(new_capacity < target->capacity && new_capacity < (size_t)(target->size/{self.capacity_threshold})) new_capacity = target->capacity; /* prevent the new capacity to fall below minimum required for original set's elements */
        if(new_capacity < 8) new_capacity = 8; /* enforce minimum viable capacity */
        assert(target->size <= new_capacity); /* require the new capacity to be large enough for the set to contain all original elements */
        if(new_capacity != target->capacity) {{
          {self.create_capacity(_target, "new_capacity")};
          if(target->elements) {{
            for(index = 0; index < target->capacity; ++index) {{
              if({self.slot.primed(target_slot)}) {{
                {self.element.copy(self.locate_slot(_target, "&_index", target_element), target_element)}; /* direct planting in order to prevent from triggering the subsequent resizings */
              }}
            }}
            _target.size = target->size;
            {self.destroy(m.target)};
          }}
          *target = _target;
        }}
      """
    
    with self.find_view as m:
      m.code = f"""
        size_t index;
        assert(target);
        assert({self.is_element(m.element)});
        if({self.locate_element(m.target, "&index", m.element)}) {{
          return {self.element.variable("target->elements[index]").bind(m.result)};
        }}
        return ({self.element.view_type})NULL;
      """
    
    with self.destroy as m:
      if self.slot.destructible:
        m.code = f"""
          size_t index;
          assert(target);
          if(target->elements) {{
            for(index = 0; index < target->capacity; ++index)
              {self.slot.destroy(target_slot)};
            {self.memory.free(target_elements)};
          }}
        """
      else:
        m.code = f"""
          assert(target);
          if(target->elements) {{
            {self.memory.free(target_elements)};
          }}
        """

    with self.empty as m:
      m.inline_code = f"""
        assert(target);
        return target->size == 0;
      """
    
    with self.put as m:
      m.code = f"""
        size_t index;
        assert(target);
        assert({self.is_element(m.element)});
        if(!{self.contains(m.target, m.element)}) {{
          {self.resize(m.target, "target->size+1")};
          {self.element.copy(self.locate_slot(m.target, "&index", m.element), m.element)};
          ++target->size;
          return 1;
        }} else return 0;
      """

    with self.emplace as m:
      create_args = [getattr(m, name) for name in self.element.constructor_parameters]
      _temp_elem = self.element.variable("temp_elem")
      _destroy_temp = f"{self.element.destroy(_temp_elem)};" if self.element.destructible else ""
      _move_or_copy = self.element.move if self.element.moveable else self.element.copy
      m.code = lambda m: f"""
        size_t index;
        {_temp_elem.definition};
        assert(target);
        {self.element.create(_temp_elem, *create_args)};
        if(!{self.contains(m.target, _temp_elem)}) {{
          {self.resize(m.target, "target->size+1")};
          {_move_or_copy(self.locate_slot(m.target, "&index", _temp_elem), _temp_elem)};
          ++target->size;
          return 1;
        }} else {{
          {_destroy_temp}
          return 0;
        }}
      """
    
    with self.remove as m:
      m.code = f"""
        size_t index;
        assert(target);
        assert({self.is_element(m.element)});
        if({self.locate_element(m.target, "&index", m.element)}) {{
          {self.slot.set_state(target_slot, 1)};
          --target->size;
          return 1;
        }} else return 0;
      """
    
    with self.copy as m:
      m.code = f"""
        size_t index;
        assert(target);
        assert(source);
        {self.create_size(m.target, "source->size")};
        for(index = 0; index < source->capacity; ++index) {{
          if({self.slot.primed(source_slot)}) {{
            {self.put(m.target, source_element)};
          }}
        }}
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

    range = self.range
    r = range.variable("r")
    
    with self.equal as m:
      m.code = f"""
        {r.definition};
        assert(left);
        assert(right);
        if({self.size(m.left)} == {self.size(m.right)}) {{
          for({r} = {range.new(m.left)}; !{range.empty(r)}; {range.move_front(r)}) {{
            if(!{self.contains(m.right, range.front_view(r))}) return 0;
          }}
          return 1;
        }} else return 0;
      """
    
    
  def _render_struct(self, stream, header):
    super()._render_struct(stream, header)
    stream.append(f"""
      struct {self.name} {{
        {self.slot}* elements; /**< @private */
        {std.size_t} capacity; /**< @private */
        {std.size_t} size; /**< @private */
      }};
    """)


#
class Range(_Range, Forward):
  brief = "Forward range over the set elements"

  
  def _render_struct(self, stream, header):
    super()._render_struct(stream, header)
    stream.append(f"""
      struct {self.name} {{
        {Indirection(self.iterable, constant=True)} iterable; /**< @private */
        {std.size_t} front; /**< @private */
      }};
    """)

  def _copy(self, result, parameters, **kwargs):
    return Macro(result, parameters, lambda target, source: f"{target} = {source}", **kwargs)

  def __setup__(self):
    super().__setup__()
    
    front_element = self.element.variable("target->iterable->elements[target->front]")
    front_slot = self.iterable.slot.variable("target->iterable->elements[target->front]")

    with self.method(None, "next", {"target": inout(self)}, hidden=True, visibility="internal", brief="Advance the range to the next live element (internal)") as m:
      m.code = lambda: f"""
        assert(target);
        while(!{self.empty("target")} && !{self.iterable.slot.primed(front_slot)}) ++target->front;
      """
    
    with self.method(Callable.Parameter(self), "new", {"iterable" : self.iterable}, brief="Create the range spanning the whole set",
      description="""
        Creates the range over the element table scanning for the first live slot. The
        traversal order is unspecified - it follows the table layout. The range must not
        outlive the set and the set must not be modified while the range is traversed.

        @param[in] iterable the set to span
        @return the range covering the whole set in unspecified order
      """) as m:
      result = m.result.variable("result")
      m.code = f"""
        {result.definition};
        assert(iterable);
        result.iterable = iterable;
        result.front = 0;
        {self.next("&result")};
        return {result};
      """

    with self.empty as m:
      m.code = f"""
        assert(target);
        return target->front >= target->iterable->capacity;
      """
    
    with self.front as m:
      result = m.result.variable("result")
      m.code = lambda: f"""
        {result.definition};
        assert(target);
        assert(!{self.empty(m.target)});
        assert({self.iterable.slot.primed(front_slot)});
        {self.element.copy(result, front_element)};
        return {result};
      """
        
    with self.front_view as m:
      m.code = lambda: f"""
        assert(target);
        assert(!{self.empty(m.target)});
        assert({self.iterable.slot.primed(front_slot)});
        return {front_element.bind(self.iterable.element.view_type)};
      """
    
    with self.move_front as m:
      m.code = f"""
        assert(target);
        assert(!{self.empty(m.target)});
        ++target->front;
        {self.next(m.target)};
      """    