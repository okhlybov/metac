from metac.mapping import Mapping, BidirectionalRange, _Entry
from metac.ordered import Ordered
from metac.set import Set
from metac.avl_set import Set as AVLSet
from metac.core import Indirection, enforced, Type, Orderable, Coerce


#
class Map(Mapping, Ordered):

  brief = "Ordered map from index to element backed by a binary search tree - iterates in index order"
  

  @enforced
  def __init__(self, name: str, element: Coerce[Type], index: Coerce[Orderable], set: Set & Ordered = AVLSet, *args, **kwargs):
    super().__init__(name, element, index, *args, **kwargs)
    self._set = set(
      self._decorate_component("set", abbreviate=True),
      _Entry(self._decorate_component("entry", abbreviate=True), self.element, self.index, visibility="internal"),
      visibility="internal",
      algebraic_operations=False,
    )
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

      Implemented as a binary search tree over the internal entry set.
      The closest C++ equivalent is [std::map<>](https://cppreference.com/cpp/container/map).
    """

    set = self._set
    entry = set.element
    _entry = entry.variable("entry")
    n = Indirection(set.node).variable("n")
    node_entry = entry.variable("n->element")
    node_index = entry.index.variable("n->element.index")
    _target = self._set.variable("target->set")

    with self.view as m:
      m.code = f"""
        int order;
        {n.definition};
        assert(target);
        n = target->set.root;
        while(n) {{
          order = {self.index.compare(node_index, m.index)};
          if(order == 0) return {entry.element_view(node_entry).bind(self.element.view_type)};
          n = order > 0 ? n->left : n->right;
        }}
        return ({self.element.view_type})NULL;
      """

    with self.set as m:
      m.code = f"""
        int order;
        {n.definition};
        {_entry.definition};
        assert(target);
        n = target->set.root;
        while(n) {{
          order = {self.index.compare(node_index, m.index)};
          if(order == 0) break;
          n = order > 0 ? n->left : n->right;
        }}
        if(n) {{
          {entry.replace_element(node_entry, m.element)}; /* an entry with the specified index already exists - replace its element's contents in-place */
        }} else {{
          {entry.emplace_index(_entry, m.index)};
          {entry.emplace_element(_entry, m.element)};
          {set.put(_target, _entry)}; /* put the brand new entry into the tree */
          {entry.destroy_element(_entry)};
          {entry.destroy_index(_entry)};
        }}
      """

    with self.emplace as m:
      create_args = [getattr(m, name) for name in self.element.constructor_parameters]
      m.code = f"""
        int order;
        {n.definition};
        {_entry.definition};
        assert(target);
        n = target->set.root;
        while(n) {{
          order = {self.index.compare(node_index, m.index)};
          if(order == 0) return 0;
          n = order > 0 ? n->left : n->right;
        }}
        {entry.emplace_index(_entry, m.index)};
        {entry.create_element(_entry, *create_args)};
        {set.put(_target, _entry)};
        {entry.destroy_element(_entry)};
        {entry.destroy_index(_entry)};
        return 1;
      """