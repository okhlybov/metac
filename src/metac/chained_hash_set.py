import metac.std as std
from metac.range import Forward
import metac.set
from metac.hashed import Hashed
from metac.container import _Range
from metac.core import inout, out, _type, _StructRenderer, Indirection, Callable, _ceil_power2


#
class Set(_StructRenderer, metac.set.Set, Hashed):

  brief = "Hash set of distinct elements using bucket chaining - stable element addresses, no sentinel values"

  def __init__(self, *args, capacity_threshold=1.0, dependencies=(), **kwargs):
    super().__init__(*args, dependencies=(*dependencies, _ceil_power2), **kwargs)
    self.node = _type(self._decorate_component("node"))
    self._node_p = Indirection(self.node)
    self._bucket_p = Indirection(self._node_p)
    self.capacity_threshold = capacity_threshold
    self.range = Range(self)

  @property
  def orderable(self):
    return False

  def __setup__(self):
    super().__setup__()

    self.description = f"""
      Requires the element type (@ref {self.element}) to be *Hashable* and *Comparable*.
      Supports one way element traversal via the corresponding @ref {self.range} iterator.

      Implemented as the hash table with bucket chaining.
      The closest C++ equivalent is [std::unordered_set<>](https://cppreference.com/cpp/container/unordered_set).
    """

    node_element = self.element.variable("n->element")
    source_element = self.element.variable("source_n->element")
    target_element = self.element.variable("n->element")
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
        target->buckets = NULL;
        target->capacity = target->size = 0;
      """

    with self.method(None, "allocate", {"target": inout(self), "capacity": std.size_t}, hidden=True, visibility="internal", brief="Allocate the hash table with the capacity rounded up to a power of two (internal)") as m:
      m.code = f"""
        assert(target);
        assert(capacity > 0);
        target->capacity = _metac_ceil_power2(capacity);
        target->buckets = {self.memory.allocate(self._node_p, "target->capacity", zero=True)};
        target->size = 0;
      """

    with self.method(None, ("create", "capacity"), {"target": out(self), "capacity": std.size_t}, hidden=True, visibility="internal",
      references=(self.allocate, self.create),
      brief="Create set with given capacity (internal)") as m:
      m.code = f"""
        assert(target);
        if(capacity) {{
          {self.allocate(m.target, m.capacity)};
        }} else {{
          {self.create(m.target)};
        }}
      """

    with self.method(None, ("create", "size"), {"target": out(self), "size": std.size_t},
      references=(self.create_capacity,),
      brief="Create set with estimated element count",
      description="""
        Creates the set preallocating the hash table for the estimated element count - the
        table capacity is the given estimate divided by the load factor threshold and rounded
        up to a power of two. No rehashing takes place until the set grows past the estimate.

        @param[out] target the set to construct
        @param[in] size the estimated element count used to preallocate the hash table
      """) as m:
      m.code = f"""
        assert(target);
        {self.create_capacity(m.target, f"(size_t)({m.size}/{self.capacity_threshold})")};
      """

    with self.destroy as m:
      _destroy = self.element.destroy(node_element) if self.element.destructible else str()
      m.code = f"""
        size_t index;
        {self.node}* n;
        {self.node}* _n;
        assert(target);
        if(target->buckets) {{
          for(index = 0; index < target->capacity; ++index) {{
            for(n = target->buckets[index]; n; n = _n) {{
              _n = n->next;
              {_destroy};
              {self.memory.free("n")};
            }}
          }}
          {self.memory.free("target->buckets")};
        }}
      """

    with self.method(None, "resize", {"target": inout(self), "new_size": std.size_t}, hidden=True, visibility="internal", brief="Resize hash table (internal)") as m:
      m.code = f"""
        size_t index, bucket, new_capacity;
        {self._bucket_p} buckets;
        {self.node}* n;
        {self.node}* _n;
        assert(target);
        new_capacity = _metac_ceil_power2((size_t)(new_size/{self.capacity_threshold})); /* predict new capacity after size changing respecting the desired capacity threshold */
        if(new_capacity < 8) new_capacity = 8; /* enforce minimum viable capacity */
        if(new_capacity != target->capacity) {{
          buckets = {self.memory.allocate(self._node_p, "new_capacity", zero=True)};
          for(index = 0; index < target->capacity; ++index) {{
            for(n = target->buckets[index]; n; n = _n) {{
              _n = n->next;
              bucket = {self.element.hash_lookup_hash(node_element)} & (new_capacity-1); /* rehash the node into the new bucket array */
              n->next = buckets[bucket];
              buckets[bucket] = n;
            }}
          }}
          {self.memory.free("target->buckets")};
          target->buckets = buckets;
          target->capacity = new_capacity;
        }}
      """

    with self.find_view as m:
      m.code = f"""
        size_t bucket;
        {self.node}* n;
        assert(target);
        if(!target->buckets) return ({self.element.view_type})NULL;
        bucket = {self.element.hash_lookup_hash(m.element)} & (target->capacity-1);
        for(n = target->buckets[bucket]; n; n = n->next) {{
          if({self.element.hash_lookup_equal(node_element, m.element)}) return {node_element.bind(m.result)};
        }}
        return ({self.element.view_type})NULL;
      """

    with self.put as m:
      m.code = f"""
        size_t bucket;
        {self.node}* n;
        assert(target);
        if({self.contains(m.target, m.element)}) return 0;
        {self.resize(m.target, "target->size+1")};
        bucket = {self.element.hash_lookup_hash(m.element)} & (target->capacity-1);
        n = {self.memory.allocate(self.node)};
        {self.element.copy(node_element, m.element)};
        n->next = target->buckets[bucket];
        target->buckets[bucket] = n;
        ++target->size;
        return 1;
      """

    # Insertion of an element whose absence the caller has already verified - moves
    # the source into the fresh node when the element type is movable, sparing the
    # deep copy and admitting the moveable-but-not-copyable elements for the
    # map-level set()/emplace() callers
    with self.method("int", "plant", {"target": inout(self), "element": inout(self.element)}, hidden=True, visibility="internal",
      constraint=lambda: self.element.copyable or self.element.moveable, brief="Plant a verified-absent element into the table (internal)") as m:
      _insert = self.element.move if self.element.moveable else self.element.copy
      m.code = f"""
        size_t bucket;
        {self.node}* n;
        assert(target);
        {self.resize(m.target, "target->size+1")};
        bucket = {self.element.hash_lookup_hash(m.element)} & (target->capacity-1);
        n = {self.memory.allocate(self.node)};
        {_insert(node_element, m.element)};
        n->next = target->buckets[bucket];
        target->buckets[bucket] = n;
        ++target->size;
        return 1;
      """

    with self.emplace as m:
      create_args = [getattr(m, name) for name in self.element.constructor_parameters]
      _destroy_node = f"{self.element.destroy(node_element)};" if self.element.destructible else ""
      m.code = lambda m: f"""
        size_t bucket;
        {self.node}* n;
        {self.node}* p;
        assert(target);
        n = {self.memory.allocate(self.node)};
        {self.element.create(node_element, *create_args)};
        if(target->buckets) {{
          bucket = {self.element.hash_lookup_hash(node_element)} & (target->capacity-1);
          for(p = target->buckets[bucket]; p; p = p->next) {{
            if({self.element.hash_lookup_equal(self.element.variable("p->element"), node_element)}) {{
              {_destroy_node}
              {self.memory.free("n")};
              return 0;
            }}
          }}
        }}
        {self.resize(m.target, "target->size+1")};
        bucket = {self.element.hash_lookup_hash(node_element)} & (target->capacity-1);
        n->next = target->buckets[bucket];
        target->buckets[bucket] = n;
        ++target->size;
        return 1;
      """

    with self.remove as m:
      _destroy = self.element.destroy(self.element.variable("n->element")) if self.element.destructible else str()
      m.code = f"""
        size_t bucket;
        {self.node}* n;
        {self.node}** p;
        assert(target);
        if(!target->buckets) return 0;
        bucket = {self.element.hash_lookup_hash(m.element)} & (target->capacity-1);
        for(p = &target->buckets[bucket]; *p; p = &(*p)->next) {{
          if({self.element.hash_lookup_equal(self.element.variable("(*p)->element"), m.element)}) {{
            n = *p;
            *p = n->next;
            {_destroy};
            {self.memory.free("n")};
            --target->size;
            return 1;
          }}
        }}
        return 0;
      """

    with self.copy as m:
      m.code = f"""
        size_t index, bucket;
        {self.node}* source_n;
        {self.node}* n;
        assert(target);
        assert(source);
        {self.create_size(m.target, "source->size")};
        for(index = 0; index < source->capacity; ++index) {{
          for(source_n = source->buckets[index]; source_n; source_n = source_n->next) {{
            bucket = {self.element.hash_lookup_hash(source_element)} & (target->capacity-1); /* direct planting in order to prevent from triggering the subsequent resizings */
            n = {self.memory.allocate(self.node)};
            {self.element.copy(target_element, source_element)};
            n->next = target->buckets[bucket];
            target->buckets[bucket] = n;
            ++target->size;
          }}
        }}
      """

    with self.move as m:
      m.code = f"""
        assert(target);
        assert(source);
        target->buckets = source->buckets;
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
    stream.append(f"""
      /** @private */
      typedef struct {self.node} {self.node};
      /** @private */
      struct {self.node} {{
        {self.element} element;
        struct {self.node}* next;
      }};
    """)
    super()._render_struct(stream, header)
    stream.append(f"""
      struct {self.name} {{
        {self._bucket_p} buckets; /**< @private */
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
        {std.size_t} bucket; /**< @private */
        {self.iterable.node}* node; /**< @private */
      }};
    """)

  def __setup__(self):
    super().__setup__()

    node_element = self.element.variable("target->node->element")

    with self.method(None, "next", {"target": inout(self)}, hidden=True, visibility="internal", brief="Advance the range to the next occupied bucket (internal)") as m:
      m.code = f"""
        assert(target);
        while(!target->node && target->bucket < target->iterable->capacity) {{
          target->node = target->iterable->buckets[target->bucket];
          ++target->bucket;
        }}
      """

    with self.method(Callable.Parameter(self), "new", {"iterable": self.iterable}, brief="Create the range spanning the whole set",
      description="""
        Creates the range over the bucket chain array scanning the buckets until the first
        occupied one. The traversal order is unspecified - it follows the hash table layout.
        The range must not outlive the set and the set must not be modified while the range
        is traversed.

        @param[in] iterable the set to span
        @return the range covering the whole set in unspecified order
      """) as m:
      result = m.result.variable("result")
      m.code = f"""
        {result.definition};
        assert(iterable);
        result.iterable = iterable;
        result.bucket = 0;
        result.node = NULL;
        {self.next("&result")};
        return {result};
      """

    with self.empty as m:
      m.inline_code = f"""
        assert(target);
        return !target->node;
      """

    with self.front as m:
      result = m.result.variable("result")
      m.inline_code = f"""
        {result.definition};
        assert(target);
        assert(!{self.empty(m.target)});
        {self.element.copy(result, node_element)};
        return {result};
      """

    with self.front_view as m:
      m.inline_code = f"""
        assert(target);
        assert(!{self.empty(m.target)});
        return {node_element.bind(self.iterable.element.view_type)};
      """

    with self.move_front as m:
      m.code = f"""
        assert(target);
        assert(!{self.empty(m.target)});
        target->node = target->node->next;
        {self.next(m.target)};
      """
