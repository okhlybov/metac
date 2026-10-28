import metac.std as std
from metac.assignable import Assignable
from metac.sortable import Sortable
from metac.range import DirectAccess
from metac.sequential import Sequential
from metac.insertable import Insertable
from metac.container import _Range
from metac.core import inout, out, Indirection, _StructRenderer, Callable


#
class Vector(_StructRenderer, Assignable, Sortable, Sequential, Insertable):
  # The append-optimized direct-access container: the elements are stored in fixed size
  # chunks addressed through the chunk table which makes the growth allocation-only
  # (no element copying, stable element addresses) while keeping the O(1) indexed access
  # through the power of two chunk size shift and mask. The destruction of the destructor-less
  # element types elides the element loop entirely leaving only the chunk releases
  # which makes the teardown of the huge transient buffers O(chunks) rather than O(elements)

  # TODO direct access get/set/inset/remove etc

  brief = "Append-optimized direct access sequence container"
  
  def __init__(self, name, element, chunk_shift=16, *args, index=std.size_t, sorting_operations=True, **kwargs):
    # memset is needed to zero-initialize the elements of the types which are
    # zero initializable but not default constructible
    super().__init__(name, element, index, *args, dependencies=(std.string_h,), sorting_operations=sorting_operations, **kwargs)
    self.chunk_shift = int(chunk_shift)
    self.chunk_mask = (1 << self.chunk_shift) - 1
    self._chunk_p = Indirection(self.element)
    self._chunk_pp = Indirection(self._chunk_p)
    self.range = Range(self)

  def _element(self, target, index):
    return self.element.variable(f"{target}->chunks[({index}) >> {self.chunk_shift}][({index}) & {self.chunk_mask}]")

  def _target_size(self, target):
    return f"{target}->size"

  def __setup__(self):
    super().__setup__()

    self.description = f"""
      Requires the element type (@ref {self.element}) to be *Copyable*.
      Supports two way element traversal via the corresponding @ref {self.range} iterator
      as well as subranging with direct indexed access to the subrange's elements.

      Implemented as the fixed size chunks of elements addressed through the chunk table -
      the append is allocation-only with the stable element addresses.
      No direct C++ equivalent, but close to [std::deque<>](https://cppreference.com/cpp/container/deque).
    """

    with self.size as m:
      m.inline_code = f"""
        assert(target);
        return target->size;
      """

    with self.empty as m:
      m.inline_code = f"""
        assert(target);
        return target->size == 0;
      """

    with self.create as m:
      m.inline_code = f"""
        assert(target);
        target->chunks = NULL;
        target->chunk_count = target->chunk_capacity = target->size = 0;
      """

    with self.indexed as m:
      m.inline_code = f"""
        assert(target);
        return {m.index} < target->size;
      """

    with self.method(None, "extend", {"target": inout(self)}, hidden=True, visibility="internal", brief="Extend chunk table if needed (internal)") as m:
      m.code = f"""
        size_t index;
        {self._chunk_pp} chunks;
        assert(target);
        if(target->size == (target->chunk_count << {self.chunk_shift})) {{
          if(target->chunk_count == target->chunk_capacity) {{
            chunks = {self.memory.allocate(self._chunk_p, "(target->chunk_capacity ? target->chunk_capacity*2 : 8)")};
            assert(chunks);
            for(index = 0; index < target->chunk_count; ++index) chunks[index] = target->chunks[index];
            {self.memory.free("target->chunks")};
            target->chunks = chunks;
            target->chunk_capacity = target->chunk_capacity ? target->chunk_capacity*2 : 8;
          }}
          target->chunks[target->chunk_count] = {self.memory.allocate(self.element, f"{1 << self.chunk_shift}")};
          assert(target->chunks[target->chunk_count]);
          ++target->chunk_count;
        }}
      """

    with self.destroy as m:
      if self.element.destructible:
        m.code = f"""
          size_t index;
          assert(target);
          if(target->chunks) {{
            for(index = 0; index < target->size; ++index) {{
              {self.element.destroy(self.element.variable("target->chunks[index >> "f"{self.chunk_shift}][index & {self.chunk_mask}]"))};
            }}
            for(index = 0; index < target->chunk_count; ++index) {{
              {self.memory.free("target->chunks[index]")};
            }}
            {self.memory.free("target->chunks")};
          }}
        """
      else:
        m.code = f"""
          size_t index;
          assert(target);
          if(target->chunks) {{
            for(index = 0; index < target->chunk_count; ++index) {{
              {self.memory.free("target->chunks[index]")};
            }}
            {self.memory.free("target->chunks")};
          }}
        """

    with self.method(None, "push", {"target": inout(self), "element": self.element}, constraint=lambda: self.element.copyable,
      references=(self.extend,),
      brief="Add element to back",
      description="""
        Appends the element in amortized O(1): the element lands in the last chunk and a fresh
        chunk of the fixed tier capacity is allocated when the current one fills up. Existing
        element addresses stay valid since the chunks never move.

        @param[in,out] target the vector to add to
        @param[in] element the element to add to the back
      """) as m:
      m.code = lambda m: f"""
        assert(target);
        {self.extend(m.target)};
        {self.element.copy(self.element.variable(f"target->chunks[target->size >> {self.chunk_shift}][target->size & {self.chunk_mask}]"), m.element)};
        ++target->size;
      """

    # Ownership-transferring counterpart of push - moves the caller's element into
    # the fresh back slot, sparing the deep copy for the movable element types
    with self.method(None, ("push", "move"), {"target": inout(self), "element": inout(self.element)}, hidden=True, visibility="internal",
      constraint=lambda: self.element.moveable, references=(self.extend,), brief="Move element to back (internal)") as m:
      m.code = lambda m: f"""
        assert(target);
        {self.extend(m.target)};
        {self.element.move(self.element.variable(f"target->chunks[target->size >> {self.chunk_shift}][target->size & {self.chunk_mask}]"), m.element)};
        ++target->size;
      """

    with self.method(None, ("emplace", "back"), {"target": inout(self)} | self.element.constructor_parameters,
      constraint=lambda: self.element.emplaceable,
      references=(self.extend,),
      brief="Construct element in-place at back",
      description="""
        Constructs the element in-place with forwarded parameters at the back in amortized O(1).
        Existing element addresses stay valid since chunks never move.

        @param[in,out] target the vector to add to
      """) as m:
      create_args = [getattr(m, name) for name in self.element.constructor_parameters]
      m.code = f"""
        assert(target);
        {self.extend(m.target)};
        {self.element.create(self.element.variable(f"target->chunks[target->size >> {self.chunk_shift}][target->size & {self.chunk_mask}]"), *create_args)};
        ++target->size;
      """
    self.macro("emplace", None, {"target": inout(self)} | self.element.constructor_parameters, lambda target, *args: self.emplace_back(target, *args),
      constraint=lambda: self.element.emplaceable, brief="Construct element in-place at back (synonym for emplace_back)")

    with self.method(self.element, "pop", {"target": inout(self)}, constraint=lambda: self.element.moveable, brief="Remove and return element from back",
      description="""
        Moves the last element out in O(1). The chunk that became empty is not released -
        it is reused by the subsequent push operations.

        @param[in,out] target the vector to remove from - must not be empty
        @return the removed back element
      """) as m:
      result = m.result.variable("result")
      m.code = f"""
        {result.definition};
        assert(target);
        assert(!{self.empty(m.target)});
        --target->size;
        {self.element.move(result, self.element.variable(f"target->chunks[target->size >> {self.chunk_shift}][target->size & {self.chunk_mask}]"))};
        return {result};
      """

    with self.put as m:
      m.inline_code = f"""
        assert(target);
        {self.push(m.target, m.element)};
        return 1;
      """

    curr_var = self._element("target", "index")
    next_var = self._element("target", "index + 1")
    with self.remove as m:
      def _remove(m):
        dest_curr = f"{self.element.destroy(curr_var)};" if self.element.destructible else ""
        dest_next = f"{self.element.destroy(next_var)};" if self.element.destructible else ""
        move_shift = (
          f"{self.element.move(curr_var, next_var)};"
          if self.element.moveable else
          f"{self.element.copy(curr_var, next_var)}; {dest_next}"
        )
        return f"""
          size_t index;
          assert(target);
          for(index = 0; index < target->size; ++index) {{
            if({self.element.equal(curr_var, m.element)}) {{
              {dest_curr}
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

    # Resize grows the vector by extending the chunk table and default-initializing the
    # new elements in place - no element migration is ever needed since the chunks are
    # stable. Shrinking destroys the removed tail and releases the chunks which became
    # fully unused; the chunk table itself is not reallocated down
    resize_slot = lambda index: f"target->chunks[{index} >> {self.chunk_shift}][{index} & {self.chunk_mask}]"
    resize_destroy_i = str(self.element.destroy(self.element.variable(resize_slot("index")))) + ";" if self.element.destructible else str()
    if self.element.default_constructible:
      resize_create_i = str(self.element.create(self.element.variable(resize_slot("target->size")))) + ";"
    else:
      resize_create_i = f"memset(&({resize_slot('target->size')}), 0, sizeof({self.element}));"

    with self.method(None, "resize", {"target": inout(self), "size": self.index}, constraint=lambda: self.element.default_constructible or self.element.zero_initializable,
      references=(self.extend,),
      brief="Resize the vector to the given number of elements",
      description="""
        Changes the number of elements: growing default-initializes the new elements in place
        extending the chunk table - no element migration is ever needed since the chunks are
        stable, so existing element addresses remain valid. Shrinking destroys the removed tail
        and releases the chunks which became fully unused; the chunk table itself is not
        reallocated down.

        @param[in,out] target the vector to resize
        @param[in] size the new number of elements - the tail is destroyed when shrinking and default-initialized when growing
      """) as m:
      m.code = f"""
        size_t index;
        size_t needed;
        assert(target);
        for(index = target->size; index < {m.size}; ++index) {{
          {self.extend(m.target)};
          {resize_create_i}
          ++target->size;
        }}
        if({m.size} < target->size) {{
          for(index = {m.size}; index < target->size; ++index) {{
            {resize_destroy_i}
          }}
          needed = ({m.size} + {self.chunk_mask}) >> {self.chunk_shift};
          for(index = needed; index < target->chunk_count; ++index) {{
            {self.memory.free("target->chunks[index]")};
          }}
          target->chunk_count = needed;
        }}
        target->size = {m.size};
      """

    with self.get as m:
      result = m.result.variable("result")
      m.inline_code = lambda m: f"""
        {result.definition};
        assert(target);
        assert({self.indexed(m.target, m.index)});
        {self.element.copy(result, self.element.variable(f"target->chunks[{m.index} >> {self.chunk_shift}][{m.index} & {self.chunk_mask}]"))};
        return {result};
      """

    # FIXME explicit casting here and there in the respective Range type is a kind of hack to deal with double pointer types
    # Normally Pointer type should be responsible for handling the per-indirection constness flags
    with self.view as m:
      m.inline_code = f"""
        assert(target);
        assert({self.indexed(m.target, m.index)});
        return {self.element.variable(f"target->chunks[{m.index} >> {self.chunk_shift}][{m.index} & {self.chunk_mask}]").bind(m.result)};
      """

    destroy_i = str(self.element.destroy(self.element.variable(f"target->chunks[index >> {self.chunk_shift}][index & {self.chunk_mask}]"))) + ";" if self.element.destructible else str()

    with self.set as m:
      m.inline_code = lambda m: f"""
        assert(target);
        assert({self.indexed(m.target, m.index)});
        {destroy_i}
        {self.element.copy(self.element.variable(f"target->chunks[{m.index} >> {self.chunk_shift}][{m.index} & {self.chunk_mask}]"), m.element)};
      """

    with self.method(None, ("create", "size"), {"target": out(self), "size": self.index}, constraint=lambda: self.element.default_constructible or self.element.zero_initializable, brief="Create the vector with room for the given number of default-constructed elements",
      description="""
        Creates the vector holding the given number of default-initialized elements laid out
        over the fixed capacity chunks. Zero-initializable elements are initialized by the
        zeroed chunk allocations alone; otherwise the elements are default constructed one by one.

        @param[out] target the vector to construct
        @param[in] size the number of default-initialized elements to provide room for
      """) as m:
      if self.element.zero_initializable:
        # The chunked zeroed allocation is the default initialization - no per element operations
        m.code = f"""
          size_t index, needed;
          assert(target);
          if({m.size} > 0) {{
            needed = ({m.size} + {self.chunk_mask}) >> {self.chunk_shift};
            target->chunks = {self.memory.allocate(self._chunk_p, "needed")};
            target->chunk_capacity = needed;
            for(index = 0; index < needed; ++index) {{
              target->chunks[index] = {self.memory.allocate(self.element, f"{1 << self.chunk_shift}", zero=True)};
            }}
            target->chunk_count = needed;
            target->size = {m.size};
          }} else {{
            {self.create(m.target)};
          }}
        """
      else:
        m.code = f"""
          size_t index;
          assert(target);
          {self.create(m.target)};
          for(index = 0; index < {m.size}; ++index) {{
            {self.extend(m.target)};
            {self.element.create(self.element.variable(f"target->chunks[target->size >> {self.chunk_shift}][target->size & {self.chunk_mask}]"))};
            ++target->size;
          }}
        """

    with self.copy as m:
      m.code = lambda m: f"""
        size_t index;
        assert(target);
        assert(source);
        {self.create(m.target)};
        for(index = 0; index < source->size; ++index) {{
          {self.extend(m.target)};
          {self.element.copy(self.element.variable(f"target->chunks[target->size >> {self.chunk_shift}][target->size & {self.chunk_mask}]"), self.element.variable(f"source->chunks[index >> {self.chunk_shift}][index & {self.chunk_mask}]"))};
          ++target->size;
        }}
      """

    with self.move as m:
      m.code = f"""
        assert(target);
        assert(source);
        target->chunks = source->chunks;
        target->chunk_count = source->chunk_count;
        target->chunk_capacity = source->chunk_capacity;
        target->size = source->size;
        {self.create(m.source)};
      """



  def _render_struct(self, stream, header):
    super()._render_struct(stream, header)
    stream.append(f"""
      struct {self.name} {{
        {self._chunk_pp} chunks; /**< @private */
        {std.size_t} chunk_count; /**< @private */
        {std.size_t} chunk_capacity; /**< @private */
        {std.size_t} size; /**< @private */
      }};
    """)


#
class Range(_Range, DirectAccess):

  brief = "Direct access range over the tiered vector elements"

  def _render_struct(self, stream, header):
    super()._render_struct(stream, header)
    stream.append(f"""
      struct {self.name} {{
        {Indirection(self.iterable, constant=True)} iterable; /**< @private */
        {std.size_t} front, back; /**< @private */
      }};
    """)

  def __setup__(self):
    super().__setup__()

    with self.method(Callable.Parameter(self), "new", {"iterable": self.iterable}, brief="Create the range spanning the whole tiered vector",
      description="""
        Creates the range over the chunked element storage. The range must not outlive
        the vector and the vector must not be resized while the range is traversed.

        @param[in] iterable the tiered vector to span
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
