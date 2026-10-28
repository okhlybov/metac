import metac.std as std
from metac.mapping import Mapping, BidirectionalRange, _Entry
from metac.flat_set import Set as FlatSet
from metac.set import Set
from metac.ordered import Ordered
from metac.core import inout, enforced


#
class Map(Mapping, Ordered):

  brief = "Flat map from index to element backed by a contiguous sorted array of key-value pairs"

  @enforced
  def _make_set(self, backend: Set & Ordered = FlatSet):
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

      Implemented as a contiguous sorted array of key-value pairs (Array-of-Structures layout) with binary search lookup.
      Provides O(log n) lookup, O(n) insertion, and superior cache locality over tree-based maps.
      The closest C++ equivalent is [std::flat_map<>](https://en.cppreference.com/w/cpp/container/flat_map) / `boost::container::flat_map`.
    """

    set = self._set
    entry = set.element
    _entry = entry.variable("entry")
    entry_mid = entry.variable("target->set.elements[mid]")
    index_mid = entry.index.variable("target->set.elements[mid].index")
    _target = self._set.variable("target->set")

    with self.method(std.size_t, "capacity", {"target": self}, brief="Get the current allocated capacity",
      description="""
        Returns the number of key-value entries the map can hold without reallocating storage.

        @param[in] target the map to query
        @return the current capacity
      """) as m:
      m.inline_code = f"""
        assert(target);
        return {self._set.capacity(_target)};
      """

    with self.method(None, "reserve", {"target": inout(self), "capacity": std.size_t}, brief="Reserve storage capacity",
      description="""
        Ensures the map has allocated storage for at least the given number of entries.

        @param[in,out] target the map to expand
        @param[in] capacity the minimum capacity to reserve
      """) as m:
      m.inline_code = f"""
        assert(target);
        {self._set.reserve(_target, m.capacity)};
      """

    with self.method(None, "compact", {"target": inout(self)}, brief="Compact storage to fit current size",
      description="""
        Reduces the allocated capacity to match the current number of entries.

        @param[in,out] target the map to compact
      """) as m:
      m.inline_code = f"""
        assert(target);
        {self._set.compact(_target)};
      """

    with self.view as m:
      m.code = f"""
        size_t low, high, mid;
        int order;
        assert(target);
        low = 0;
        high = target->set.size;
        while(low < high) {{
          mid = low + (high - low) / 2;
          order = {self.index.compare(index_mid, m.index)};
          if(order == 0) return {entry.element_view(entry_mid).bind(self.element.view_type)};
          if(order < 0) low = mid + 1;
          else high = mid;
        }}
        return ({self.element.view_type})NULL;
      """

    with self.set as m:
      # The probe loop terminates with low at the exact insertion position - the
      # entry is planted right there instead of re-searching through the set's put
      m.code = f"""
        size_t low, high, mid;
        int order;
        {_entry.definition};
        assert(target);
        low = 0;
        high = target->set.size;
        while(low < high) {{
          mid = low + (high - low) / 2;
          order = {self.index.compare(index_mid, m.index)};
          if(order == 0) {{
            {entry.replace_element(entry_mid, m.element)};
            return;
          }}
          if(order < 0) low = mid + 1;
          else high = mid;
        }}
        {entry.emplace_index(_entry, m.index)};
        {entry.emplace_element(_entry, m.element)};
        {set.insert_at(_target, "low", _entry)};
        {entry.destroy_element(_entry)};
        {entry.destroy_index(_entry)};
      """

    with self.emplace as m:
      create_args = [getattr(m, name) for name in self.element.constructor_parameters]
      m.code = f"""
        size_t low, high, mid;
        int order;
        {_entry.definition};
        assert(target);
        low = 0;
        high = target->set.size;
        while(low < high) {{
          mid = low + (high - low) / 2;
          order = {self.index.compare(index_mid, m.index)};
          if(order == 0) return 0;
          if(order < 0) low = mid + 1;
          else high = mid;
        }}
        {entry.emplace_index(_entry, m.index)};
        {entry.create_element(_entry, *create_args)};
        {set.move_at(_target, "low", _entry)};
        {entry.destroy_element(_entry)};
        {entry.destroy_index(_entry)};
        return 1;
      """

