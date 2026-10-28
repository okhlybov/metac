from metac.mapping import Mapping, BidirectionalRange, _Entry
from metac.btree_set import Set as BTreeSet
from metac.set import Set
from metac.ordered import Ordered
from metac.core import Indirection, enforced


#
class Map(Mapping, Ordered):

  brief = "Ordered map from index to element backed by a B-Tree - iterates in index order"

  @enforced
  def _make_set(self, backend: Set & Ordered = BTreeSet, **kwargs):
    return backend(
      self._decorate_component("set", abbreviate=True),
      _Entry(self._decorate_component("entry", abbreviate=True), self.element, self.index, visibility="internal"),
      visibility="internal",
      algebraic_operations=False,
      **kwargs,
    )

  def __init__(self, name, element, index, *args, order=4, node_capacity=None, **kwargs):
    super().__init__(name, element, index, *args, **kwargs)
    set_kws = {}
    if node_capacity is not None:
      set_kws["node_capacity"] = node_capacity
    else:
      set_kws["order"] = order
    self._set = self._make_set(**set_kws)
    self.dependencies.add(self._set)
    self._setup_range()

  def _setup_range(self):
    # The backend iterates in ascending index order - the bidirectional wrapper is
    # selected statically, never probed from the built component
    self.range = BidirectionalRange(self)

  @property
  def orderable(self):
    return True

  def __setup__(self):
    super().__setup__()

    self.description = f"""
      Requires the index type (@ref {self.index}) to be *Orderable* and the element type (@ref {self.element}) to be *Copyable*.
      Supports one way traversal over the indices and elements via the corresponding @ref {self.range} iterator - the entries are yielded in index order.

      Implemented as a B-Tree over the internal entry set.
      Provides cache-friendly contiguous node layout and reduced allocator pressure compared to binary tree maps.
      The closest C++ equivalent is [absl::btree_map<>](https://abseil.io/docs/cpp/guides/container#abslbtree_map) / `boost::container::btree_map`.
    """

    set = self._set
    entry = set.element
    _entry = entry.variable("entry")
    n = Indirection(set.node).variable("n")
    _target = self._set.variable("target->set")

    with self.view as m:
      m.code = f"""
        {n.definition};
        int order;
        size_t low, high, mid;
        assert(target);
        n = target->set.root;
        while(n) {{
          low = 0;
          high = n->count;
          while(low < high) {{
            mid = low + (high - low) / 2;
            order = {self.index.compare(self.index.variable("n->elements[mid].index"), m.index)};
            if(order == 0) return {entry.element_view(entry.variable("n->elements[mid]")).bind(self.element.view_type)};
            if(order < 0) low = mid + 1;
            else high = mid;
          }}
          if(n->is_leaf) break;
          n = n->children[low];
        }}
        return ({self.element.view_type})NULL;
      """

    with self.set as m:
      m.code = f"""
        {n.definition};
        {_entry.definition};
        int order;
        size_t low, high, mid;
        {set.node}* found_node = NULL;
        size_t found_idx = 0;
        assert(target);
        n = target->set.root;
        while(n) {{
          low = 0;
          high = n->count;
          while(low < high) {{
            mid = low + (high - low) / 2;
            order = {self.index.compare(self.index.variable("n->elements[mid].index"), m.index)};
            if(order == 0) {{
              found_node = n;
              found_idx = mid;
              break;
            }}
            if(order < 0) low = mid + 1;
            else high = mid;
          }}
          if(found_node) break;
          if(n->is_leaf) break;
          n = n->children[low];
        }}
        if(found_node) {{
          {entry.replace_element(entry.variable("found_node->elements[found_idx]"), m.element)};
        }} else {{
          {entry.emplace_index(_entry, m.index)};
          {entry.emplace_element(_entry, m.element)};
          {set.plant(_target, _entry)};
          {entry.destroy_element(_entry)};
          {entry.destroy_index(_entry)};
        }}
      """

    with self.emplace as m:
      create_args = [getattr(m, name) for name in self.element.constructor_parameters]
      m.code = f"""
        {n.definition};
        {_entry.definition};
        int order;
        size_t low, high, mid;
        assert(target);
        n = target->set.root;
        while(n) {{
          low = 0;
          high = n->count;
          while(low < high) {{
            mid = low + (high - low) / 2;
            order = {self.index.compare(self.index.variable("n->elements[mid].index"), m.index)};
            if(order == 0) return 0;
            if(order < 0) low = mid + 1;
            else high = mid;
          }}
          if(n->is_leaf) break;
          n = n->children[low];
        }}
        {entry.emplace_index(_entry, m.index)};
        {entry.create_element(_entry, *create_args)};
        {set.plant(_target, _entry)};
        {entry.destroy_element(_entry)};
        {entry.destroy_index(_entry)};
        return 1;
      """
