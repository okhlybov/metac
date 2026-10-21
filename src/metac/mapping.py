import metac.std as std
from metac.record import Record
from metac.core import inout, Callable, _StructRenderer, Macro, enforced, Type, Comparable, Orderable, Coerce
from metac.container import _Range
from metac.range import Forward, Bidirectional
from metac.traversable import Traversable
from metac.assignable import Assignable


# Common entry implementation for maps backed by an underlying set
class _Entry(Record):
  
  def __init__(self, name, element, index, visibility, *args, **kwargs):
    super().__init__(name, {"element": element, "index": index}, *args, visibility=visibility, getters=False, setters=False, **kwargs)
    self.index = self.fields["index"]
    self.element = self.fields["element"]
    self.element_p = self.element.view_type
    self.index_p = self.index.view_type

  def __setup__(self):
    super().__setup__()

    _index = self.index.variable("target->index")
    _element = self.element.variable("target->element")

    with self.method(Callable.Parameter(self.element_p), ("element", "view"), {"target": self}, hidden=True, visibility="internal", brief="Get view of element (internal)") as m:
      m.code = f"""
        assert(target);
        return {self.element.variable("target->element").bind(m.result)};
      """

    with self.method(Callable.Parameter(self.index_p), ("index", "view"), {"target": self}, hidden=True, visibility="internal", brief="Get view of index (internal)") as m:
      m.code = f"""
        assert(target);
        return {self.index.variable("target->index").bind(m.result)};
      """

    with self.method(None, ("emplace", "index"), {"target": inout(self), "index": self.index}, hidden=True, visibility="internal", constraint=lambda: self.index.copyable, brief="Emplace index (internal)") as m:
      m.code = f"""
        assert(target);
        {self.index.copy(_index, m.index)};
      """

    with self.method(None, ("destroy", "index"), {"target": inout(self)}, hidden=True, visibility="internal", brief="Destroy index (internal)") as m:
      if self.index.destructible:
        m.code = f"""
          assert(target);
          {self.index.destroy(_index)};
        """
      else:
        m.code = f"""
          assert(target);
        """
      
    with self.method(None, ("emplace", "element"), {"target": inout(self), "element": self.element}, hidden=True, visibility="internal", constraint=lambda: self.element.copyable, brief="Emplace element (internal)") as m:
      m.code = lambda m: f"""
        assert(target);
        {self.element.copy(_element, m.element)};
      """

    with self.method(None, ("create", "element"), {"target": inout(self)} | self.element.constructor_parameters, hidden=True, visibility="internal", constraint=lambda: self.element.emplaceable, brief="Create element in-place (internal)") as m:
      def _create_element(m):
        create_args = [getattr(m, name) for name in self.element.constructor_parameters]
        return f"""
          assert(target);
          {self.element.create(_element, *create_args)};
        """
      m.code = _create_element

    with self.method(None, ("destroy", "element"), {"target": inout(self)}, hidden=True, visibility="internal", brief="Destroy element (internal)") as m:
      if self.element.destructible:
        m.code = f"""
          assert(target);
          {self.element.destroy(_element)};
        """
      else:
        m.code = f"""
          assert(target);
        """

    with self.method(None, ("replace", "element"), {"target": inout(self), "element": self.element}, hidden=True, visibility="internal", constraint=lambda: self.element.copyable, brief="Replace element in-place (internal)") as m:
      m.code = lambda m: f"""
        assert(target);
        {self.destroy_element(m.target)};
        {self.element.copy(_element, m.element)};
      """

    self.hash_lookup_hash = Macro(std.size_t, {"target": self}, lambda target: str(self.index.hash( self.index.variable(f"(({target}).index)") )))
    self.hash_lookup_equal = Macro("int", {"left": self, "right": self}, lambda left, right: str(self.index.equal( self.index.variable(f"(({left}).index)"), self.index.variable(f"(({right}).index)") )))

    # The entries are identified by their indices alone so the ordered containers holding them
    # must compare them by the index as well - the hash-based backends need no ordering and
    # stay usable over non-orderable indices
    if self.index.comparable:
      with self.equal as m:
        m.code = f"""
          assert(left);
          assert(right);
          return {self.index.equal(self.index.variable("((left)->index)"), self.index.variable("((right)->index)"))};
        """

    if self.index.orderable:
      with self.compare as m:
        m.code = f"""
          assert(left);
          assert(right);
          return {self.index.compare(self.index.variable("((left)->index)"), self.index.variable("((right)->index)"))};
        """
  
  @property
  def orderable(self):
    # The entries are ordered by their indices alone - the element is the payload - and
    # only when the index itself is orderable
    return self.index.orderable

  @property
  def hashable(self):
    return self.index.hashable

  @property
  def comparable(self):
    return self.index.comparable

  @property
  def constructible(self):
    return False


# Common Forward range for mappings
class Range(_Range, Forward):

  brief = "Forward range over the mapping indices and elements"

  def __init__(self, iterable, *args, **kwargs):
    super().__init__(iterable, *args, **kwargs)
    self._range = iterable._set.range
    self._entry = iterable._set.element
    self.index = iterable.index
    self.dependencies.update((self._entry, self._range))

  def _render_struct(self, stream, header):
    super()._render_struct(stream, header)
    stream.append(f"""
      struct {self.name} {{
        {self._range.name} range; /**< @private */
      }};
    """)

  def __setup__(self):
    super().__setup__()

    _target_range = self._range.variable("target->range")
    is_ordered = self.iterable.orderable
    order_doc = "in ascending index order" if is_ordered else "in unspecified order"
    front_doc = "the lowest index" if is_ordered else "the entry found first in the table layout"

    with self.method(Callable.Parameter(self), "new", {"iterable": self.iterable}, brief="Create the range spanning the whole mapping",
      description=f"""
        Creates the range over the mapping which starts at the first entry and
        proceeds {order_doc}. The range must not outlive the mapping and the mapping
        must not be modified while the range is traversed.

        @param[in] iterable the mapping to span
        @return the range covering the whole mapping {order_doc}
      """) as m:
      result = m.result.variable("result")
      m.code = f"""
        {result.definition};
        assert(iterable);
        result.range = {self._range.new(f"&{m.iterable}->set")};
        return {result};
      """

    with self.empty as m:
      m.code = f"""
        assert(target);
        return {self._range.empty(_target_range)};
      """

    with self.method(self.index.view_type, ("index", "front", "view"), {"target": self}, brief="Get view of front index",
      description=f"""
        Returns a pointer to the index of {front_doc}.
        The view is valid while that entry is held by the mapping.

        @param[in] target the non-empty range to inspect
        @return a constant view of the front index
      """) as m:
      m.code = f"""
        assert(target);
        assert(!{self.empty(m.target)});
        return {self._entry.index_view(self._range.front_view(_target_range)).bind(self.index.view_type)};
      """

    with self.front as m:
      result = m.result.variable("result")
      m.code = f"""
        {result.definition};
        assert(target);
        assert(!{self.empty(m.target)});
        {self.element.copy(result, self._entry.element_view(self._range.front_view(_target_range)))};
        return {result};
      """

    with self.front_view as m:
      m.code = f"""
        assert(target);
        assert(!{self.empty(m.target)});
        return {self._entry.element_view(self._range.front_view(_target_range)).bind(self.element.view_type)};
      """

    with self.method(self.index, ("index", "front"), {"target": self}, constraint=lambda: self.index.copyable, brief="Get front index",
      description=f"""
        Returns a copy of the index of {front_doc}.

        @param[in] target the non-empty range to inspect
        @return a copy of the front index
      """) as m:
      result = m.result.variable("result")
      m.code = f"""
        {result.definition};
        assert(target);
        assert(!{self.empty(m.target)});
        {self.index.copy(result, self._entry.index_view(self._range.front_view(_target_range)))};
        return {result};
      """

    with self.move_front as m:
      m.code = f"""
        assert(target);
        assert(!{self.empty(m.target)});
        {self._range.move_front(_target_range)};
      """


# Bidirectional range over the mapping indices and elements - instantiated for the mappings
# whose underlying set provides a backward-walkable range (the ordered backends)
class BidirectionalRange(Range, Bidirectional):

  brief = "Bidirectional range over the mapping indices and elements"

  def __setup__(self):
    super().__setup__()

    _target_range = self._range.variable("target->range")

    with self.method(self.element.view_type, ("back", "view"), {"target": self}, brief="Get view of back element",
      description="""
        Returns a pointer to the last element without copying it.
        The view is valid while that entry is held by the mapping.

        @param[in] target the non-empty range to inspect
        @return a constant view of the back element
      """) as m:
      m.code = f"""
        assert(target);
        assert(!{self.empty(m.target)});
        return {self._entry.element_view(self._range.back_view(_target_range)).bind(self.element.view_type)};
      """

    with self.back as m:
      result = m.result.variable("result")
      m.code = f"""
        {result.definition};
        assert(target);
        assert(!{self.empty(m.target)});
        {self.element.copy(result, self._entry.element_view(self._range.back_view(_target_range)))};
        return {result};
      """

    with self.method(self.index.view_type, ("index", "back", "view"), {"target": self}, brief="Get view of back index",
      description="""
        Returns a pointer to the index of the last entry.
        The view is valid while that entry is held by the mapping.

        @param[in] target the non-empty range to inspect
        @return a constant view of the back index
      """) as m:
      m.code = f"""
        assert(target);
        assert(!{self.empty(m.target)});
        return {self._entry.index_view(self._range.back_view(_target_range)).bind(self.index.view_type)};
      """

    with self.method(self.index, ("index", "back"), {"target": self}, constraint=lambda: self.index.copyable, brief="Get back index",
      description="""
        Returns a copy of the index of the last entry.

        @param[in] target the non-empty range to inspect
        @return a copy of the back index
      """) as m:
      result = m.result.variable("result")
      m.code = f"""
        {result.definition};
        assert(target);
        assert(!{self.empty(m.target)});
        {self.index.copy(result, self._entry.index_view(self._range.back_view(_target_range)))};
        return {result};
      """

    with self.move_back as m:
      m.code = f"""
        assert(target);
        assert(!{self.empty(m.target)});
        {self._range.move_back(_target_range)};
      """


# Abstract base class for all associative key-value maps backed by an underlying Set
class Mapping(_StructRenderer, Traversable, Assignable):

  brief = "Abstract associative container mapping keys (indices) to values (elements) backed by an underlying set"

  @enforced
  def __init__(self, name: str, element: Coerce[Type], index: Coerce[Comparable | Orderable], *args, **kwargs):
    super().__init__(name, element, index, *args, **kwargs)

  def _ordering(self):
    # The keyed containers order their indices, not their payload elements
    return self.index

  def _hashing(self):
    # The keyed containers hash their indices, not their payload elements
    return self.index

  def _setup_range(self):
    # The abstract mapping range walks forward only; the ordered map subclasses override
    # this hook with the bidirectional wrapper since their backends iterate in ascending
    # order - the knowledge is static per concrete module, never probed from the instance
    self.range = Range(self)

  def _render_struct(self, stream, header):
    super()._render_struct(stream, header)
    stream.append(f"""
      struct {self.name} {{
        {self._set.variable("set").definition}; /**< @private */
      }};
    """)

  def __setup__(self):
    super().__setup__()

    _target = self._set.variable("target->set")
    _source = self._set.variable("source->set")
    _left = self._set.variable("left->set")
    _right = self._set.variable("right->set")

    with self.create as m:
      m.code = f"""
        assert(target);
        {self._set.create(_target)};
      """

    with self.destroy as m:
      m.code = f"""
        assert(target);
        {self._set.destroy(_target)};
      """

    with self.copy as m:
      m.code = f"""
        assert(target);
        assert(source);
        {self._set.copy(_target, _source)};
      """

    with self.move as m:
      m.code = f"""
        assert(target);
        assert(source);
        {self._set.move(_target, _source)};
      """

    with self.equal as m:
      m.code = lambda m: f"""
        assert(left);
        assert(right);
        return {self._set.equal(_left, _right)};
      """

    if self.orderable:
      with self.compare as m:
        m.code = lambda m: f"""
          assert(left);
          assert(right);
          return {self._set.compare(_left, _right)};
        """

    with self.hash as m:
      m.code = lambda m: f"""
        assert(target);
        return {self._set.hash(_target)};
      """

    with self.empty as m:
      m.code = f"""
        assert(target);
        return {self._set.empty(_target)};
      """

    with self.size as m:
      m.code = f"""
        assert(target);
        return {self._set.size(_target)};
      """

    set = self._set
    entry = set.element

    with self.indexed as m:
      m.code = f"""
        assert(target);
        return {self.view(m.target, m.index)} != NULL;
      """

    with self.get as m:
      _element_p = entry.element_p.variable("element_p")
      result = m.result.variable("result")
      m.code = f"""
        {_element_p.definition};
        {result.definition};
        assert(target);
        {_element_p} = ({_element_p.type}){self.view(m.target, m.index)};
        if(!{_element_p}) abort();
        {self.element.copy(result, _element_p)};
        return {result};
      """

    _entry = entry.variable("entry")

    with self.method("int", "remove", {"target": inout(self), "index": self.index}, brief="Remove entry with specified index",
      description="""
        Removes the key-value entry associated with `index` from the map, if present.

        @param[in,out] target the map to modify
        @param[in] index the key to remove
        @return 1 if an entry was removed, 0 if not found
      """) as m:
      m.code = f"""
        {_entry.definition};
        int removed;
        assert(target);
        {entry.emplace_index(_entry, m.index)};
        removed = {set.remove(_target, _entry)};
        {entry.destroy_index(_entry)};
        return removed;
      """

    self.method("int", "emplace", {"target": inout(self), "index": self.index} | self.element.constructor_parameters,
      constraint=lambda: (self.index.comparable or self.index.orderable) and self.element.emplaceable,
      brief="Construct element in-place for key if not present",
      description="""
        If `index` is not already present in the map, constructs a new element in-place
        with the forwarded parameters and associates it with `index`.
        Returns 1 if a new entry was emplaced, 0 if `index` was already present.

        @param[in,out] target the map to update
        @param[in] index the key to associate with
        @return 1 if newly emplaced, 0 if key already exists
      """)

