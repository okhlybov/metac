import metac.std as std
from metac.core import _StructRenderer, Callable, inout, enforced, Comparable, Coerce
from metac.container import _Range
from metac.multiset import Multiset
from metac.mapping import Mapping
from metac.flat_map import Map as FlatMap
from metac.range import Forward


# Multiset container tracking element frequencies
class Counter(_StructRenderer, Multiset):

  brief = "Multiset container tracking element frequencies"

  @enforced
  def __init__(self, name: str, element: Coerce[Comparable], backend: Mapping = FlatMap, *args, algebraic_operations=True, dependencies=(), **kwargs):
    super().__init__(name, element, *args, algebraic_operations=algebraic_operations, dependencies=(*dependencies, std.string_h), **kwargs)
    self._map = backend(
      self._decorate_component("map", abbreviate=True),
      std.size_t,
      self.element,
      visibility="internal",
    )
    self.dependencies.add(self._map)
    self.range = Range(self)

  @property
  def constructible(self):
    return True

  @property
  def default_constructible(self):
    return True

  @property
  def destructible(self):
    return True

  @property
  def copyable(self):
    return True

  @property
  def moveable(self):
    return True

  @property
  def swappable(self):
    return True

  @property
  def comparable(self):
    return True

  @property
  def orderable(self):
    return self._map.orderable

  @property
  def hashable(self):
    return True

  def _render_struct(self, stream, header):
    super()._render_struct(stream, header)
    stream.append(f"""
      struct {self.name} {{
        {self._map.name} map; /**< @private */
        size_t total_size; /**< @private */
      }};
    """)

  def __setup__(self):
    super().__setup__()

    self.description = f"""
      Multiset / frequency counter tracking occurrences of unique @ref {self.element} values.
      Backed by an internal map mapping elements to their multiplicity counters.

      Tracks both total multiplicity (`size`) and unique element count (`distinct_size`) in O(1).
      Supports frequency queries, incremental add/remove, and multiset set algebra.
    """

    _target = self._map.variable("target->map")
    _source = self._map.variable("source->map")
    _left = self._map.variable("left->map")
    _right = self._map.variable("right->map")

    with self.create as m:
      m.code = f"""
        assert(target);
        {self._map.create(_target)};
        target->total_size = 0;
      """

    with self.destroy as m:
      m.code = f"""
        assert(target);
        {self._map.destroy(_target)};
      """

    with self.copy as m:
      m.code = f"""
        assert(target);
        assert(source);
        {self._map.copy(_target, _source)};
        target->total_size = source->total_size;
      """

    with self.move as m:
      m.code = f"""
        assert(target);
        assert(source);
        {self._map.move(_target, _source)};
        target->total_size = source->total_size;
        source->total_size = 0;
      """

    with self.swap as m:
      m.code = f"""
        size_t tmp_size;
        assert(left);
        assert(right);
        {self._map.swap(_left, _right)};
        tmp_size = left->total_size;
        left->total_size = right->total_size;
        right->total_size = tmp_size;
      """

    with self.equal as m:
      m.code = f"""
        assert(left);
        assert(right);
        if(left->total_size != right->total_size) return 0;
        return {self._map.equal(_left, _right)};
      """

    if self.orderable:
      with self.compare as m:
        m.code = f"""
          assert(left);
          assert(right);
          return {self._map.compare(_left, _right)};
        """

    with self.hash as m:
      m.code = f"""
        assert(target);
        return {self._map.hash(_target)};
      """

    with self.empty as m:
      m.code = f"""
        assert(target);
        return target->total_size == 0;
      """

    with self.size as m:
      m.code = f"""
        assert(target);
        return target->total_size;
      """

    with self.method(std.size_t, ("total", "size"), {"target": self}, brief="Get total number of elements including duplicates",
      description="""
        Returns the sum of multiplicities across all elements in the counter in O(1).

        @param[in] target the counter to measure
        @return the total element count
      """) as m:
      m.code = f"""
        assert(target);
        return target->total_size;
      """

    with self.method(std.size_t, ("distinct", "size"), {"target": self}, brief="Get number of unique elements",
      description="""
        Returns the number of distinct elements present in the counter in O(1).

        @param[in] target the counter to measure
        @return the count of distinct elements
      """) as m:
      m.code = f"""
        assert(target);
        return {self._map.size(_target)};
      """

    with self.method(None, "clear", {"target": inout(self)}, brief="Clear all elements from counter",
      description="""
        Removes all elements from the counter, resetting total and distinct sizes to zero.

        @param[in,out] target the counter to clear
      """) as m:
      m.code = f"""
        assert(target);
        {self._map.destroy(_target)};
        {self._map.create(_target)};
        target->total_size = 0;
      """

    with self.count as m:
      m.code = f"""
        const size_t* v;
        assert(target);
        v = (const size_t*){self._map.view(_target, m.element)};
        return v ? *v : 0;
      """

    with self.contains as m:
      m.code = f"""
        assert(target);
        return {self.count(m.target, m.element)} > 0;
      """

    with self.method(None, "add", {"target": inout(self), "element": self.element, "count": std.size_t}, brief="Add element with multiplicity",
      description="""
        Increments the multiplicity of the element by `count`.
        If the element is not already present, it is inserted with multiplicity `count`.

        @param[in,out] target the counter to modify
        @param[in] element the element to add
        @param[in] count the multiplicity to add
      """) as m:
      m.code = f"""
        const size_t* v;
        assert(target);
        if(count == 0) return;
        v = (const size_t*){self._map.view(_target, m.element)};
        if(v) {{
          {self._map.set(_target, m.element, "*v + count")};
        }} else {{
          {self._map.set(_target, m.element, "count")};
        }}
        target->total_size += count;
      """

    with self.method(std.size_t, "subtract", {"target": inout(self), "element": self.element, "count": std.size_t}, brief="Subtract element multiplicity",
      description="""
        Decrements the multiplicity of the element by at most `count`.
        If the remaining multiplicity reaches zero, the element is removed from the counter.

        @param[in,out] target the counter to modify
        @param[in] element the element to remove
        @param[in] count the maximum multiplicity to remove
        @return the number of occurrences actually removed
      """) as m:
      m.code = f"""
        const size_t* v;
        size_t old_count, removed;
        assert(target);
        if(count == 0) return 0;
        v = (const size_t*){self._map.view(_target, m.element)};
        if(!v) return 0;
        old_count = *v;
        if(old_count <= count) {{
          removed = old_count;
          {self._map.remove(_target, m.element)};
        }} else {{
          removed = count;
          {self._map.set(_target, m.element, "old_count - count")};
        }}
        target->total_size -= removed;
        return removed;
      """

    with self.method(std.size_t, ("remove", "count"), {"target": inout(self), "element": self.element, "count": std.size_t}, brief="Remove element multiplicity",
      description="""
        Decrements the multiplicity of the element by at most `count`.
        Alias for `subtract`.

        @param[in,out] target the counter to modify
        @param[in] element the element to remove
        @param[in] count the maximum multiplicity to remove
        @return the number of occurrences actually removed
      """) as m:
      m.inline_code = lambda m: f"""
        return {self.subtract(m.target, m.element, m.count)};
      """

    with self.put as m:
      m.code = f"""
        assert(target);
        {self.add(m.target, m.element, 1)};
        return 1;
      """

    with self.emplace as m:
      def _emplace_code(m):
        create_args = [getattr(m, name) for name in self.element.constructor_parameters]
        _temp = self.element.variable("temp")
        _destroy_temp = f"{self.element.destroy(_temp)};" if self.element.destructible else ""
        return f"""
          {_temp.definition};
          assert(target);
          {self.element.create(_temp, *create_args)};
          {self.add(m.target, _temp, 1)};
          {_destroy_temp}
          return 1;
        """
      m.code = _emplace_code

    with self.remove as m:
      m.code = f"""
        const size_t* v;
        size_t old_count;
        assert(target);
        v = (const size_t*){self._map.view(_target, m.element)};
        if(!v) return 0;
        old_count = *v;
        if(old_count <= 1) {{
          {self._map.remove(_target, m.element)};
        }} else {{
          {self._map.set(_target, m.element, "old_count - 1")};
        }}
        target->total_size -= 1;
        return 1;
      """

    with self.wipe as m:
      m.code = f"""
        const size_t* v;
        size_t old_count;
        assert(target);
        v = (const size_t*){self._map.view(_target, m.element)};
        if(!v) return 0;
        old_count = *v;
        {self._map.remove(_target, m.element)};
        target->total_size -= old_count;
        return old_count;
      """

    with self.method(std.size_t, ("remove", "all"), {"target": inout(self), "element": self.element}, brief="Remove all occurrences of element",
      description="""
        Completely removes the element from the counter regardless of its multiplicity.
        Alias for `wipe`.

        @param[in,out] target the counter to modify
        @param[in] element the element to remove completely
        @return the multiplicity removed
      """) as m:
      m.inline_code = lambda m: f"""
        return {self.wipe(m.target, m.element)};
      """

    with self.equal_range as m:
      result = m.result.variable("result")
      m.code = lambda m: f"""
        {result.definition};
        size_t cnt;
        assert(target);
        cnt = {self.count(m.target, m.element)};
        result.counter = target;
        result.is_single = 1;
        result.single_count = cnt;
        result.single_view = {self.find_view(m.target, m.element)};
        return {result};
      """

    # --- Algebraic multiset operations ---
    r = self.range.variable("r")

    with self.apply_union as m:
      m.code = lambda m: f"""
        size_t added = 0;
        {r.definition};
        assert(target);
        assert(other);
        if(target == other) return 0;
        for({r} = {self.range.new(m.other)}; !{self.range.empty(r)}; {self.range.move_front(r)}) {{
          size_t o_cnt = {self.range.count(r)};
          size_t t_cnt = {self.count(m.target, self.range.front_view(r))};
          if(o_cnt > t_cnt) {{
            {self.add(m.target, self.range.front_view(r), "o_cnt - t_cnt")};
            added += o_cnt - t_cnt;
          }}
        }}
        return added;
      """

    with self.apply_difference as m:
      m.code = lambda m: f"""
        size_t removed = 0;
        {r.definition};
        assert(target);
        assert(other);
        if(target == other) {{
          removed = target->total_size;
          {self.clear(m.target)};
          return removed;
        }}
        for({r} = {self.range.new(m.other)}; !{self.range.empty(r)}; {self.range.move_front(r)}) {{
          size_t o_cnt = {self.range.count(r)};
          removed += {self.subtract(m.target, self.range.front_view(r), "o_cnt")};
        }}
        return removed;
      """

    with self.apply_intersection as m:
      temp = self.variable("temp")
      m.code = lambda m: f"""
        size_t removed = 0;
        {self.name} {temp};
        {r.definition};
        assert(target);
        assert(other);
        if(target == other) return 0;
        {self.create(temp)};
        {self.copy(temp, m.target)};
        for({r} = {self.range.new(temp)}; !{self.range.empty(r)}; {self.range.move_front(r)}) {{
          size_t t_cnt = {self.range.count(r)};
          size_t o_cnt = {self.count(m.other, self.range.front_view(r))};
          if(o_cnt == 0) {{
            removed += {self.wipe(m.target, self.range.front_view(r))};
          }} else if(t_cnt > o_cnt) {{
            removed += {self.subtract(m.target, self.range.front_view(r), "t_cnt - o_cnt")};
          }}
        }}
        {self.destroy(temp)};
        return removed;
      """

    with self.apply_symmetric_difference as m:
      temp = self.variable("temp")
      m.code = lambda m: f"""
        size_t changed = 0;
        {self.name} {temp};
        {r.definition};
        assert(target);
        assert(other);
        if(target == other) {{
          changed = target->total_size;
          {self.clear(m.target)};
          return changed;
        }}
        {self.create(temp)};
        for({r} = {self.range.new(m.other)}; !{self.range.empty(r)}; {self.range.move_front(r)}) {{
          size_t o_cnt = {self.range.count(r)};
          size_t t_cnt = {self.count(m.target, self.range.front_view(r))};
          if(o_cnt > t_cnt) {{
            {self.add(temp, self.range.front_view(r), "o_cnt - t_cnt")};
          }}
          if(t_cnt > 0) {{
            size_t rem = t_cnt > o_cnt ? o_cnt : t_cnt;
            changed += {self.subtract(m.target, self.range.front_view(r), "rem")};
          }}
        }}
        for({r} = {self.range.new(temp)}; !{self.range.empty(r)}; {self.range.move_front(r)}) {{
          size_t cnt = {self.range.count(r)};
          {self.add(m.target, self.range.front_view(r), "cnt")};
          changed += cnt;
        }}
        {self.destroy(temp)};
        return changed;
      """

    with self.create_union as m:
      m.code = lambda m: f"""
        assert(target);
        assert({m.left});
        assert({m.right});
        assert(target != {m.left} && target != {m.right}); /* the target must be fresh storage */
        if({m.left} == {m.right}) {{
          {self.copy(m.target, m.left)};
          return;
        }}
        {r.definition};
        if({m.left}->total_size >= {m.right}->total_size) {{
          {self.copy(m.target, m.left)};
          for({r} = {self.range.new(m.right)}; !{self.range.empty(r)}; {self.range.move_front(r)}) {{
            size_t o_cnt = {self.range.count(r)};
            size_t t_cnt = {self.count(m.target, self.range.front_view(r))};
            if(o_cnt > t_cnt) {{
              {self.add(m.target, self.range.front_view(r), "o_cnt - t_cnt")};
            }}
          }}
        }} else {{
          {self.copy(m.target, m.right)};
          for({r} = {self.range.new(m.left)}; !{self.range.empty(r)}; {self.range.move_front(r)}) {{
            size_t o_cnt = {self.range.count(r)};
            size_t t_cnt = {self.count(m.target, self.range.front_view(r))};
            if(o_cnt > t_cnt) {{
              {self.add(m.target, self.range.front_view(r), "o_cnt - t_cnt")};
            }}
          }}
        }}
      """

    with self.create_intersection as m:
      m.code = lambda m: f"""
        assert(target);
        assert({m.left});
        assert({m.right});
        assert(target != {m.left} && target != {m.right}); /* the target must be fresh storage */
        if({m.left} == {m.right}) {{
          {self.copy(m.target, m.left)};
          return;
        }}
        {r.definition};
        {self.create(m.target)};
        if({self.distinct_size(m.left)} <= {self.distinct_size(m.right)}) {{
          for({r} = {self.range.new(m.left)}; !{self.range.empty(r)}; {self.range.move_front(r)}) {{
            size_t o_cnt = {self.count(m.right, self.range.front_view(r))};
            if(o_cnt > 0) {{
              size_t l_cnt = {self.range.count(r)};
              {self.add(m.target, self.range.front_view(r), "l_cnt < o_cnt ? l_cnt : o_cnt")};
            }}
          }}
        }} else {{
          for({r} = {self.range.new(m.right)}; !{self.range.empty(r)}; {self.range.move_front(r)}) {{
            size_t o_cnt = {self.count(m.left, self.range.front_view(r))};
            if(o_cnt > 0) {{
              size_t r_cnt = {self.range.count(r)};
              {self.add(m.target, self.range.front_view(r), "r_cnt < o_cnt ? r_cnt : o_cnt")};
            }}
          }}
        }}
      """

    with self.create_difference as m:
      m.code = lambda m: f"""
        assert(target);
        assert({m.left});
        assert({m.right});
        assert(target != {m.left} && target != {m.right}); /* the target must be fresh storage */
        if({m.left} == {m.right}) {{
          {self.create(m.target)};
          return;
        }}
        if({m.right}->total_size == 0) {{
          {self.copy(m.target, m.left)};
          return;
        }}
        {r.definition};
        {self.create(m.target)};
        for({r} = {self.range.new(m.left)}; !{self.range.empty(r)}; {self.range.move_front(r)}) {{
          size_t l_cnt = {self.range.count(r)};
          size_t r_cnt = {self.count(m.right, self.range.front_view(r))};
          if(l_cnt > r_cnt) {{
            {self.add(m.target, self.range.front_view(r), "l_cnt - r_cnt")};
          }}
        }}
      """

    with self.create_symmetric_difference as m:
      m.code = lambda m: f"""
        assert(target);
        assert({m.left});
        assert({m.right});
        assert(target != {m.left} && target != {m.right}); /* the target must be fresh storage */
        if({m.left} == {m.right}) {{
          {self.create(m.target)};
          return;
        }}
        {r.definition};
        {self.create(m.target)};
        for({r} = {self.range.new(m.left)}; !{self.range.empty(r)}; {self.range.move_front(r)}) {{
          size_t l_cnt = {self.range.count(r)};
          size_t r_cnt = {self.count(m.right, self.range.front_view(r))};
          if(l_cnt > r_cnt) {{
            {self.add(m.target, self.range.front_view(r), "l_cnt - r_cnt")};
          }}
        }}
        for({r} = {self.range.new(m.right)}; !{self.range.empty(r)}; {self.range.move_front(r)}) {{
          size_t r_cnt = {self.range.count(r)};
          size_t l_cnt = {self.count(m.left, self.range.front_view(r))};
          if(r_cnt > l_cnt) {{
            {self.add(m.target, self.range.front_view(r), "r_cnt - l_cnt")};
          }}
        }}
      """

    with self.is_subset as m:
      m.code = lambda m: f"""
        {r.definition};
        assert(target);
        assert(other);
        if(target == other) return 1;
        if(target->total_size > other->total_size) return 0;
        for({r} = {self.range.new(m.target)}; !{self.range.empty(r)}; {self.range.move_front(r)}) {{
          size_t t_cnt = {self.range.count(r)};
          size_t o_cnt = {self.count(m.other, self.range.front_view(r))};
          if(t_cnt > o_cnt) return 0;
        }}
        return 1;
      """

    with self.is_superset as m:
      m.code = lambda m: f"""
        assert(target);
        assert(other);
        return {self.is_subset(m.other, m.target)};
      """


# Range iterator over unique elements and their counts
class Range(_Range, Forward):

  brief = "Forward range over unique elements and their counts in Counter"

  def __init__(self, iterable, *args, **kwargs):
    super().__init__(iterable, *args, **kwargs)
    self._map_range = iterable._map.range
    self.element = iterable.element
    self.dependencies.add(self._map_range)

  def _render_struct(self, stream, header):
    super()._render_struct(stream, header)
    stream.append(f"""
      struct {self.name} {{
        {self._map_range.name} range; /**< @private */
        const {self.iterable.name}* counter; /**< @private */
        {self.element.view_type} single_view; /**< @private */
        size_t single_count; /**< @private */
        int is_single; /**< @private */
      }};
    """)

  def __setup__(self):
    super().__setup__()

    order_doc = "in ascending element order" if self.iterable.orderable else "in unspecified map order"

    self.description = f"""
      Iterates over distinct elements held in @ref {self.iterable.name} {order_doc}.
      Yields the element value/view and its multiplicity count at each step.
    """

    _range = self._map_range.variable("target->range")

    with self.method(Callable.Parameter(self), "new", {"iterable": self.iterable}, brief="Create range over counter",
      description=f"""
        Creates a range over the counter, yielding distinct elements and their counts {order_doc}.

        @param[in] iterable the counter to span
        @return the range covering the counter
      """) as m:
      result = m.result.variable("result")
      m.code = f"""
        {result.definition};
        assert(iterable);
        result.range = {self._map_range.new(f"&{m.iterable}->map")};
        result.counter = iterable;
        result.single_count = 0;
        result.is_single = 0;
        return {result};
      """

    with self.empty as m:
      m.code = f"""
        assert(target);
        if(target->is_single) return target->single_count == 0;
        return {self._map_range.empty(_range)};
      """

    with self.move_front as m:
      m.code = f"""
        assert(target);
        if(target->is_single) {{
          target->single_count = 0;
          return;
        }}
        {self._map_range.move_front(_range)};
      """

    with self.front_view as m:
      m.code = f"""
        assert(target);
        if(target->is_single) return target->single_view;
        return {self._map_range.index_front_view(_range)};
      """

    with self.front as m:
      result = m.result.variable("result")
      m.code = f"""
        assert(target);
        if(target->is_single) {{
          {result.definition};
          {self.element.copy(result, self.element.view_type.variable("target->single_view"))};
          return {result};
        }}
        return {self._map_range.index_front(_range)};
      """

    with self.method(std.size_t, "count", {"target": self}, brief="Get multiplicity of current element",
      description="""
        Returns the multiplicity count of the element at the current range position.

        @param[in] target the range to read
        @return the multiplicity count
      """) as m:
      m.code = f"""
        assert(target);
        if(target->is_single) return target->single_count;
        return *{self._map_range.front_view(_range)};
      """
