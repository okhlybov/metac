import metac.set
import metac.flat_sets
from metac.flat_sets import Range


#
class Set(metac.flat_sets.Set, metac.set.Set):

  brief = "Contiguous sorted array set with binary search lookup and cache-friendly layout"

  def __init__(self, name, element, *args, **kwargs):
    super().__init__(name, element, *args, **kwargs)

  def __setup__(self):
    super().__setup__()

    self.description = f"""
      Requires the element type (@ref {self.element}) to be *Orderable* and *Copyable*.
      Supports bidirectional element traversal and direct indexed access via the corresponding @ref {self.range} iterator - elements are yielded in ascending order.

      Implemented as a contiguous sorted dynamic array with binary search lookup.
      Provides O(log n) lookup, O(n) insertion and deletion, and superior cache locality over tree-based sets.
      The closest C++ equivalent is [std::flat_set<>](https://en.cppreference.com/w/cpp/container/flat_set) / `boost::container::flat_set`.
    """

    with self.put as m:
      m.references.add(self.lower_bound)
      pos_code = f"""
        size_t pos, i;
        assert(target);
        pos = {self.lower_bound(m.target, m.element)};
        if(pos < target->size && !{self.element.compare(self._element(m.target, "pos"), m.element)}) {{
          return 0;
        }}
      """
      m.code = self._insert_at_code(pos_code, "pos", m.element)

    with self.emplace as m:
      m.references.add(self.lower_bound)
      def _emplace_code(m):
        create_args = [getattr(m, name) for name in self.element.constructor_parameters]
        _temp_elem = self.element.variable("temp_elem")
        _destroy_temp = f"{self.element.destroy(_temp_elem)};" if self.element.destructible else ""
        pos_code = f"""
          size_t pos, i;
          {_temp_elem.definition};
          assert(target);
          {self.element.create(_temp_elem, *create_args)};
          pos = {self.lower_bound(m.target, _temp_elem)};
          if(pos < target->size && !{self.element.compare(self._element(m.target, "pos"), _temp_elem)}) {{
            {_destroy_temp}
            return 0;
          }}
        """
        return self._move_at_code(pos_code, "pos", _temp_elem)
      m.code = _emplace_code


