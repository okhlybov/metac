import metac.std as std


# Mixin class providing binary search and bisection algorithms for direct-access containers.
class Bisectable:

  def __init__(self, *args, bisection_operations=True, bisection_optional_group=None, search_optional_group=None, **kwargs):
    self.bisection_operations = bool(bisection_operations)
    self.bisection_optional_group = bisection_optional_group
    super().__init__(*args, **kwargs)

  # Protocol handlers
  
  # def _element(self, target, index):
  #   pass

  # def _target_size(self, target):
  #   pass

  def __setup__(self):
    super().__setup__()

    self.dependencies.add(std.size_t) # FIXME move to dependencies
    bisect_constraint = lambda: self.bisection_operations and self.element.orderable

    with self.method(std.size_t, ("lower", "bound"), {"target": self, "element": self.element}, constraint=bisect_constraint, optional_group=self.bisection_optional_group, brief="Get the first position the element can be inserted at keeping the order",
      description="""
        Binary searches the sorted container in O(log n) returning the leftmost position the
        element can be inserted at keeping the ascending order. The container must be sorted
        in the ascending order beforehand.

        @param[in] target the sorted container to search
        @param[in] element the element to insert
        @return the position of the first element not less than the given one
      """) as m:
      m.code = lambda m: f"""
        size_t low, high, mid;
        assert(target);
        low = 0;
        high = {self._target_size(m.target)};
        while(low < high) {{
          mid = low + (high - low)/2;
          if({self.element.compare(self._element(m.target, "mid"), m.element)} < 0) low = mid + 1;
          else high = mid;
        }}
        return low;
      """

    with self.method(std.size_t, ("upper", "bound"), {"target": self, "element": self.element}, constraint=bisect_constraint, optional_group=self.bisection_optional_group, brief="Get the last position the element can be inserted at keeping the order",
      description="""
        Binary searches the sorted container in O(log n) returning the rightmost position the
        element can be inserted at keeping the ascending order. The container must be sorted
        in the ascending order beforehand.

        @param[in] target the sorted container to search
        @param[in] element the element to compare with
        @return the position of the first element greater than the given one
      """) as m:
      m.code = lambda m: f"""
        size_t low, high, mid;
        assert(target);
        low = 0;
        high = {self._target_size(m.target)};
        while(low < high) {{
          mid = low + (high - low)/2;
          if({self.element.compare(self._element(m.target, "mid"), m.element)} <= 0) low = mid + 1;
          else high = mid;
        }}
        return low;
      """

    with self.method("int", ("binary", "search"), {"target": self, "element": self.element}, constraint=bisect_constraint, optional_group=self.bisection_optional_group, references=(self.lower_bound,), brief="Check if the element is present in the sorted container",
      description="""
        Binary searches the sorted container in O(log n) for the element. The container must be
        sorted in the ascending order beforehand.

        @param[in] target the sorted container to search
        @param[in] element the element to look for
        @return non-zero if the element is present in the container
      """) as m:
      m.code = lambda m: f"""
        size_t low;
        assert(target);
        low = {self.lower_bound(m.target, m.element)};
        return low < {self._target_size(m.target)} && !{self.element.compare(self._element(m.target, "low"), m.element)};
      """