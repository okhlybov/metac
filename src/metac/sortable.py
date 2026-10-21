import metac.std as std
from metac.core import inout
from metac.bisectable import Bisectable


# Mixin class providing in-place sorting, reversal, and binary search algorithms
# for direct-access sequence containers.
class Sortable(Bisectable):

  def __init__(self, *args, sorting_operations=True, **kwargs):
    self.sorting_operations = bool(sorting_operations)
    super().__init__(*args, bisection_operations=sorting_operations, bisection_optional_group="sorting_operations", **kwargs)

  def __setup__(self):
    super().__setup__()

    sort_constraint = lambda: self.sorting_operations and self.element.orderable and self.element.copyable and self.element.swappable
    reverse_constraint = lambda: self.sorting_operations and self.element.swappable
    search_constraint = lambda: self.sorting_operations and self.element.orderable

    element_i = lambda target="target": self._element(target, "i")
    element_j = lambda target="target": self._element(target, "j")
    element_lo = lambda target="target": self._element(target, "lo")
    element_mid = lambda target="target": self._element(target, "mid")
    element_hi = lambda target="target": self._element(target, "hi")
    element_prev = lambda target="target": self._element(target, "j-1")
    pivot = self.element.variable("pivot")

    with self.method(None, ("sort", "insertion"), {"target": inout(self), "lo": std.size_t, "hi": std.size_t}, hidden=True, visibility="internal", constraint=sort_constraint, brief="Sort range using insertion sort (internal)") as m:
      m.code = lambda m: f"""
        size_t i, j;
        assert(target);
        for(i = {m.lo} + 1; i <= {m.hi}; ++i) {{
          for(j = i; j > {m.lo} && {self.element.compare(element_prev(m.target), element_j(m.target))} > 0; --j) {{
            {self.element.swap(element_prev(m.target), element_j(m.target))};
          }}
        }}
      """

    with self.method(None, ("sort", "range"), {"target": inout(self), "lo": std.size_t, "hi": std.size_t}, hidden=True, visibility="internal", constraint=sort_constraint, references=(self.sort_insertion,), brief="Sort range using quicksort (internal)") as m:
      m.code = lambda m: f"""
        size_t i, j, mid;
        {pivot.definition};
        assert(target);
        while({m.lo} < {m.hi}) {{
          if({m.hi} - {m.lo} < 16) {{ /* small ranges are insertion sorted */
            {self.sort_insertion(m.target, m.lo, m.hi)};
            return;
          }}
          mid = {m.lo} + ({m.hi} - {m.lo})/2;
          /* median of three orders the lo, mid and hi elements protecting against the sorted inputs */
          if({self.element.compare(element_mid(m.target), element_lo(m.target))} < 0) {self.element.swap(element_mid(m.target), element_lo(m.target))};
          if({self.element.compare(element_hi(m.target), element_mid(m.target))} < 0) {{
            {self.element.swap(element_hi(m.target), element_mid(m.target))};
            if({self.element.compare(element_mid(m.target), element_lo(m.target))} < 0) {self.element.swap(element_mid(m.target), element_lo(m.target))};
          }}
          {self.element.copy(pivot, element_mid(m.target))};
          i = {m.lo};
          j = {m.hi};
          while(i <= j) {{
            while({self.element.compare(element_i(m.target), pivot)} < 0) ++i;
            while({self.element.compare(element_j(m.target), pivot)} > 0) --j;
            if(i >= j) break;
            {self.element.swap(element_i(m.target), element_j(m.target))};
            ++i;
            --j;
          }}
          {str(self.element.destroy(pivot)) + ";" if self.element.destructible else str()}
          /* recursing into the smaller part and iterating over the larger one bounds the recursion depth */
          if(j - {m.lo} < {m.hi} - i) {{
            {self.sort_range(m.target, m.lo, "j")};
            {m.lo} = i;
          }} else {{
            {self.sort_range(m.target, "i", m.hi)};
            {m.hi} = j;
          }}
        }}
      """

    with self.method(None, "sort", {"target": inout(self)}, constraint=sort_constraint, optional_group="sorting_operations", references=(self.sort_range,), brief="Sort elements in ascending order",
      description="""
        Sorts the elements in ascending order in expected O(n log n) with a quicksort
        variant: ranges of less than 16 elements are insertion sorted, the pivot is the
        median of three which protects against the sorted inputs, and the recursion always
        descends into the smaller part to bound the depth. The sort is not stable and needs
        the element to be Orderable, Copyable and Swappable.

        @param[in,out] target the container to sort
      """) as m:
      m.code = lambda m: f"""
        assert(target);
        if({self._target_size(m.target)} > 1) {self.sort_range(m.target, 0, f"{self._target_size(m.target)}-1")};
      """

    # Reversal is a pure exchange loop so it requires nothing but the element swappability
    with self.method(None, "reverse", {"target": inout(self)}, constraint=reverse_constraint, optional_group="sorting_operations", brief="Reverse the order of elements",
      description="""
        Reverses the element order in place in O(n) by exchanging the mirrored element
        pairs. It needs nothing but the element swappability - no copies or destructions
        take place.

        @param[in,out] target the container to reverse
      """) as m:
      m.code = lambda m: f"""
        size_t i;
        assert(target);
        for(i = 0; i < {self._target_size(m.target)}/2; ++i) {{
          {self.element.swap(self._element(m.target, "i"), self._element(m.target, f"{self._target_size(m.target)}-1-i"))};
        }}
      """

    with self.method("int", "sorted", {"target": self}, constraint=search_constraint, optional_group="sorting_operations", brief="Check if elements are sorted in ascending order",
      description="""
        Walks the container once in O(n) returning non-zero when every element is not less
        than its predecessor. An empty or single element container is considered sorted.

        @param[in] target the container to check
        @return non-zero if the elements are sorted in ascending order
      """) as m:
      m.code = lambda m: f"""
        size_t index;
        assert(target);
        for(index = 1; index < {self._target_size(m.target)}; ++index) {{
          if({self.element.compare(self._element(m.target, "index"), self._element(m.target, "index-1"))} < 0) return 0;
        }}
        return 1;
      """
