import metac.std as std
from metac.core import inout, Callable, Indirection, enforced
from metac.container import _Range
from metac.range import Forward
from metac.mapping import _Entry
from metac.multimapping import Multimapping
from metac.multiset import Multiset
from metac.ordered import Ordered
import metac.flat_multiset


# Forward range over the flat multimap indices and elements
class Range(_Range, Forward):

  brief = "Forward range over the multimap indices and elements"

  def __init__(self, iterable, *args, dependencies=(), **kwargs):
    super().__init__(iterable, *args, dependencies=(*dependencies, std.assert_h), **kwargs)
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
    front_doc = "the lowest index" if is_ordered else "the entry found first in the layout"

    with self.method(Callable.Parameter(self), "new", {"iterable": self.iterable}, brief="Create the range spanning the whole multimap",
      description=f"""
        Creates the range over the multimap which starts at the first entry and
        proceeds {order_doc}. The range must not outlive the multimap and the multimap
        must not be modified while the range is traversed.

        @param[in] iterable the multimap to span
        @return the range covering the whole multimap {order_doc}
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
        The view is valid while that entry is held by the multimap.

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

    if hasattr(self._range, "size"):
      with self.method(std.size_t, "size", {"target": self}, brief="Get number of remaining elements in range",
        description="""
          Returns the number of elements remaining in the range in O(1).

          @param[in] target the range to measure
          @return number of elements
        """) as m:
        m.code = f"""
          assert(target);
          return {self._range.size(_target_range)};
        """


#
class Map(Multimapping, Ordered):

  brief = "Flat multimap from index to multiple elements backed by a contiguous sorted array of key-value pairs"

  @enforced
  def _make_set(self, backend: Multiset & Ordered = metac.flat_multiset.Set):
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
    self.range = Range(self)

  @property
  def orderable(self):
    return True

  def _render_struct(self, stream, header):
    super()._render_struct(stream, header)
    stream.append(f"""
      struct {self.name} {{
        {self._set.variable("set").definition}; /**< @private */
      }};
    """)

  def __setup__(self):
    super().__setup__()

    self.description = f"""
      Requires the index type (@ref {self.index}) to be *Orderable* and the element type (@ref {self.element}) to be *Copyable*.
      Supports one way traversal over the indices and elements via the corresponding @ref {self.range} iterator - the entries are yielded in index order.
      Multiple entries with equivalent keys are permitted and preserved in FIFO order.

      Implemented as a contiguous sorted array of key-value pairs (Array-of-Structures layout) with binary search lookup.
      Provides O(log n) lookup, O(n) insertion, and superior cache locality over tree-based multimaps.
      The closest C++ equivalent is [std::flat_multimap<>](https://en.cppreference.com/w/cpp/container/flat_multimap) / `boost::container::flat_multimap`.
    """

    set = self._set
    entry = set.element
    _entry = entry.variable("entry")

    _target = set.variable("target->set")
    _source = set.variable("source->set")
    _left = set.variable("left->set")
    _right = set.variable("right->set")

    with self.create as m:
      m.code = f"""
        assert(target);
        {set.create(_target)};
      """

    with self.destroy as m:
      m.code = f"""
        assert(target);
        {set.destroy(_target)};
      """

    with self.copy as m:
      m.code = f"""
        assert(target);
        assert(source);
        {set.copy(_target, _source)};
      """

    with self.move as m:
      m.code = f"""
        assert(target);
        assert(source);
        {set.move(_target, _source)};
      """

    with self.equal as m:
      m.code = f"""
        assert(left);
        assert(right);
        return {set.equal(_left, _right)};
      """

    with self.hash as m:
      m.code = f"""
        assert(target);
        return {set.hash(_target)};
      """

    with self.empty as m:
      m.code = f"""
        assert(target);
        return {set.empty(_target)};
      """

    with self.size as m:
      m.code = f"""
        assert(target);
        return {set.size(_target)};
      """

    with self.view as m:
      found = Indirection(entry, constant=True).variable("found")
      m.code = f"""
        {_entry.definition};
        {found.definition};
        assert(target);
        {entry.emplace_index(_entry, m.index)};
        {found} = ({found.type}){set.find_view(_target, _entry)};
        {entry.destroy_index(_entry)};
        if({found}) {{
          return {entry.element_view(found)};
        }}
        return ({self.element.view_type})NULL;
      """

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

    with self.put as m:
      m.code = f"""
        {_entry.definition};
        assert(target);
        {entry.emplace_index(_entry, m.index)};
        {entry.emplace_element(_entry, m.element)};
        {set.plant(_target, _entry)};
        {entry.destroy_element(_entry)};
        {entry.destroy_index(_entry)};
        return 1;
      """

    with self.emplace as m:
      def _emplace_code(m):
        create_args = [getattr(m, name) for name in self.element.constructor_parameters]
        return f"""
          {_entry.definition};
          assert(target);
          {entry.emplace_index(_entry, m.index)};
          {entry.create_element(_entry, *create_args)};
          {set.plant(_target, _entry)};
          {entry.destroy_element(_entry)};
          {entry.destroy_index(_entry)};
          return 1;
        """
      m.code = _emplace_code

    with self.remove as m:
      m.code = f"""
        {_entry.definition};
        int removed;
        assert(target);
        {entry.emplace_index(_entry, m.index)};
        removed = {set.remove(_target, _entry)};
        {entry.destroy_index(_entry)};
        return removed;
      """

    with self.wipe as m:
      m.code = f"""
        {_entry.definition};
        size_t wiped;
        assert(target);
        {entry.emplace_index(_entry, m.index)};
        wiped = {set.wipe(_target, _entry)};
        {entry.destroy_index(_entry)};
        return wiped;
      """

    with self.count as m:
      m.code = f"""
        {_entry.definition};
        size_t cnt;
        assert(target);
        {entry.emplace_index(_entry, m.index)};
        cnt = {set.count(_target, _entry)};
        {entry.destroy_index(_entry)};
        return cnt;
      """

    with self.equal_range as m:
      result = m.result.variable("result")
      m.code = f"""
        {result.definition};
        {_entry.definition};
        assert(target);
        {entry.emplace_index(_entry, m.index)};
        result.range = {set.equal_range(_target, _entry)};
        {entry.destroy_index(_entry)};
        return {result};
      """

    with self.method(std.size_t, "capacity", {"target": self}, brief="Get the current allocated capacity",
      description="""
        Returns the number of key-value entries the multimap can hold without reallocating storage.

        @param[in] target the multimap to query
        @return the current capacity
      """) as m:
      m.inline_code = f"""
        assert(target);
        return {set.capacity(_target)};
      """

    with self.method(None, "reserve", {"target": inout(self), "capacity": std.size_t}, brief="Reserve storage capacity",
      description="""
        Ensures the multimap has allocated storage for at least the given number of entries.

        @param[in,out] target the multimap to expand
        @param[in] capacity the minimum capacity to reserve
      """) as m:
      m.inline_code = f"""
        assert(target);
        {set.reserve(_target, m.capacity)};
      """

    with self.method(None, "compact", {"target": inout(self)}, brief="Compact storage to fit current size",
      description="""
        Reduces the allocated capacity to match the current number of entries.

        @param[in,out] target the multimap to compact
      """) as m:
      m.inline_code = f"""
        assert(target);
        {set.compact(_target)};
      """

    with self.compare as m:
      elem_cmp = f"""
        cmp = {self.element.compare(self.element.variable("left->set.elements[i].element"), self.element.variable("right->set.elements[i].element"))};
        if(cmp != 0) return cmp;
      """ if self.element.orderable else ""
      m.code = f"""
        size_t i, min_size;
        int cmp;
        assert(left);
        assert(right);
        min_size = left->set.size < right->set.size ? left->set.size : right->set.size;
        for(i = 0; i < min_size; ++i) {{
          cmp = {self.index.compare(self.index.variable("left->set.elements[i].index"), self.index.variable("right->set.elements[i].index"))};
          if(cmp != 0) return cmp;
          {elem_cmp}
        }}
        return left->set.size < right->set.size ? -1 : (left->set.size > right->set.size ? 1 : 0);
      """
