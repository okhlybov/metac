from metac.mapping import Mapping, _Entry
from metac.chained_hash_set import Set
import metac.set
from metac.hashed import Hashed
from metac.core import Indirection, enforced


#
class Map(Mapping, Hashed):

  brief = "Hash map from index to element using bucket chaining - stable entry addresses, no sentinel values"

  @enforced
  def _make_set(self, backend: metac.set.Set & Hashed = Set):
    return backend(
      self._decorate_component("set", abbreviate=True),
      _Entry(self._decorate_component("entry", abbreviate=True), self.element, self.index, visibility="internal"),
      visibility="internal",
      algebraic_operations=False,
    )

  def __init__(self, name, element, index, *args, **kwargs):
    super().__init__(name, element, index, *args, **kwargs)
    self._set = self._make_set()
    self.dependencies.add(self._set)
    self._setup_range()

  @property
  def orderable(self):
    return False

  def __setup__(self):
    super().__setup__()

    self.description = f"""
      Requires the index type (@ref {self.index}) to be *Hashable* and *Comparable* and the element type (@ref {self.element}) to be *Copyable*.
      Supports one way traversal over the indices and elements via the corresponding @ref {self.range} iterator.

      Implemented as the hash table with bucket chaining over the internal chained entry set.
      The closest C++ equivalent is [std::unordered_map<>](https://cppreference.com/cpp/container/unordered_map).
    """

    set = self._set
    entry = set.element
    n = Indirection(set.node).variable("n")
    node_entry = entry.variable("n->element")
    node_index = entry.index.variable("n->element.index")
    _target = self._set.variable("target->set")

    with self.view as m:
      m.code = f"""
        size_t bucket;
        {n.definition};
        assert(target);
        if(!target->set.buckets) return ({self.element.view_type})NULL;
        bucket = {self.index.hash(m.index)} & (target->set.capacity-1);
        for(n = target->set.buckets[bucket]; n; n = n->next) {{
          if({self.index.equal(node_index, m.index)}) return {entry.element_view(node_entry).bind(self.element.view_type)};
        }}
        return ({self.element.view_type})NULL;
      """

    with self.set as m:
      m.code = f"""
        size_t bucket;
        {n.definition};
        assert(target);
        bucket = {self.index.hash(m.index)} & (target->set.capacity-1);
        for(n = (target->set.buckets ? target->set.buckets[bucket] : ({n.type})NULL); n; n = n->next) {{
          if({self.index.equal(node_index, m.index)}) break;
        }}
        if(n) {{
          {entry.replace_element(node_entry, m.element)}; /* an entry with the specified index already exists - replace its element's contents in-place */
        }} else {{
          {self._set.resize(_target, "target->set.size+1")};
          bucket = {self.index.hash(m.index)} & (target->set.capacity-1); /* the capacity might have changed - recompute the bucket */
          {n} = {self.memory.allocate(set.node)};
          {entry.emplace_index(node_entry, m.index)};
          {entry.emplace_element(node_entry, m.element)};
          n->next = target->set.buckets[bucket];
          target->set.buckets[bucket] = n;
          ++target->set.size;
        }}
      """

    with self.emplace as m:
      create_args = [getattr(m, name) for name in self.element.constructor_parameters]
      m.code = f"""
        size_t bucket;
        {n.definition};
        assert(target);
        if(target->set.capacity > 0) {{
          bucket = {self.index.hash(m.index)} & (target->set.capacity-1);
          for(n = (target->set.buckets ? target->set.buckets[bucket] : ({n.type})NULL); n; n = n->next) {{
            if({self.index.equal(node_index, m.index)}) return 0;
          }}
        }}
        {self._set.resize(_target, "target->set.size+1")};
        bucket = {self.index.hash(m.index)} & (target->set.capacity-1);
        {n} = {self.memory.allocate(set.node)};
        {entry.emplace_index(node_entry, m.index)};
        {entry.create_element(node_entry, *create_args)};
        n->next = target->set.buckets[bucket];
        target->set.buckets[bucket] = n;
        ++target->set.size;
        return 1;
      """

