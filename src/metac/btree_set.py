import metac.std as std
import metac.set
from metac.ordered import Ordered
from metac.range import Bidirectional
from metac.container import _Range
from metac.core import inout, _type, _StructRenderer, Indirection, Callable


#
class Set(_StructRenderer, metac.set.Set, Ordered):

  brief = "Ordered set of distinct values implemented as a B-Tree - iterates in sorted order"

  def __init__(self, name, element, *args, order=4, node_capacity=None, dependencies=(), **kwargs):
    if node_capacity is not None:
      order = max(2, (node_capacity + 1) // 2)
    self.order = order
    super().__init__(name, element, *args, dependencies=(*dependencies, std.size_t), **kwargs)
    self.node = _type(self._decorate_component("node"))
    self._node_p = Indirection(self.node)
    self.range = Range(self)

  @property
  def orderable(self):
    return True

  @property
  def copyable(self):
    return self.element.copyable and self.element.comparable

  def __setup__(self):
    super().__setup__()

    max_keys = 2 * self.order - 1
    max_children = 2 * self.order
    min_keys = self.order - 1

    self.description = f"""
      Requires the element type (@ref {self.element}) to be *Orderable*.
      Supports bidirectional element traversal via the corresponding @ref {self.range} iterator - elements are yielded in sorted order.

      Implemented as a B-Tree with minimum degree t = {self.order} (each non-root node holds between {min_keys} and {max_keys} elements).
      Nodes store elements contiguously in array blocks for superior cache locality and significantly reduced allocator overhead compared to binary search trees.
    """

    with self.size as m:
      m.inline_code = """
        assert(target);
        return target->size;
      """

    with self.empty as m:
      m.inline_code = """
        assert(target);
        return target->size == 0;
      """

    with self.create as m:
      m.inline_code = """
        assert(target);
        target->root = NULL;
        target->size = 0;
      """

    destroy_elem = f"{self.element.destroy(self.element.variable('n->elements[i]'))};" if self.element.destructible else ""

    with self.destroy as m:
      m.code = f"""
        {self.node}* n;
        {self.node}* p;
        size_t i;
        int has_child;
        assert(target);
        n = target->root;
        while(n) {{
          if(!n->is_leaf) {{
            has_child = 0;
            for(i = 0; i <= n->count; ++i) {{
              if(n->children[i]) {{
                {self.node}* c = n->children[i];
                n->children[i] = NULL;
                n = c;
                has_child = 1;
                break;
              }}
            }}
            if(has_child) continue;
          }}
          p = n->parent;
          for(i = 0; i < n->count; ++i) {{
            {destroy_elem}
          }}
          {self.memory.free("n")};
          n = p;
        }}
      """

    with self.method(None, ("split", "child"), {"target": inout(self), "parent": Callable.Parameter(self._node_p), "i": std.size_t}, hidden=True, visibility="internal", brief="Split full child of parent (internal)") as m:
      # The moves vacate the source slots past the post-split count - a move leaves
      # the source default-constructed, so the slots whose create() allocates would
      # leak without the paired destroy
      _destroy_vacated = lambda e: f"{self.element.destroy(self.element.variable(e))};" if self.element.destructible else ""
      m.code = f"""
        {self.node}* y;
        {self.node}* z;
        size_t j;
        assert(target);
        assert(parent);
        y = parent->children[i];
        assert(y);
        assert(y->count == {max_keys});
        z = {self.memory.allocate(self.node)};
        z->is_leaf = y->is_leaf;
        z->count = {min_keys};
        z->parent = parent;
        for(j = 0; j < {max_children}; ++j) z->children[j] = NULL;

        for(j = 0; j < {min_keys}; ++j) {{
          {self.element.move(self.element.variable("z->elements[j]"), self.element.variable(f"y->elements[j + {self.order}]"))};
          {_destroy_vacated(f"y->elements[j + {self.order}]")}
        }}
        if(!y->is_leaf) {{
          for(j = 0; j < {self.order}; ++j) {{
            z->children[j] = y->children[j + {self.order}];
            y->children[j + {self.order}] = NULL;
            if(z->children[j]) z->children[j]->parent = z;
          }}
        }}
        y->count = {min_keys};

        for(j = parent->count + 1; j > i + 1; --j) {{
          parent->children[j] = parent->children[j - 1];
        }}
        parent->children[i + 1] = z;

        for(j = parent->count; j > i; --j) {{
          {self.element.move(self.element.variable("parent->elements[j]"), self.element.variable("parent->elements[j - 1]"))};
        }}
        {self.element.move(self.element.variable("parent->elements[i]"), self.element.variable(f"y->elements[{self.order - 1}]"))};
        {_destroy_vacated(f"y->elements[{self.order - 1}]")}
        ++parent->count;
      """

    mid_element = self.element.variable("node->elements[mid]")

    with self.find_view as m:
      m.code = f"""
        {self.node}* node;
        size_t low, high, mid;
        int order_cmp;
        assert(target);
        node = target->root;
        while(node) {{
          low = 0;
          high = node->count;
          while(low < high) {{
            mid = low + (high - low) / 2;
            order_cmp = {self.element.compare(mid_element, m.element)};
            if(order_cmp == 0) return {mid_element.bind(m.result)};
            if(order_cmp < 0) low = mid + 1;
            else high = mid;
          }}
          if(node->is_leaf) break;
          node = node->children[low];
        }}
        return ({self.element.view_type})NULL;
      """

    with self.put as m:
      m.code = f"""
        {self.node}* s;
        {self.node}* curr;
        size_t low, high, mid, i, j;
        int order_cmp;
        assert(target);

        if({self.find_view(m.target, m.element)} != NULL) return 0;

        if(!target->root) {{
          curr = {self.memory.allocate(self.node)};
          curr->is_leaf = 1;
          curr->count = 1;
          curr->parent = NULL;
          for(j = 0; j < {max_children}; ++j) curr->children[j] = NULL;
          {self.element.copy(self.element.variable("curr->elements[0]"), m.element)};
          target->root = curr;
          target->size = 1;
          return 1;
        }}

        if(target->root->count == {max_keys}) {{
          s = {self.memory.allocate(self.node)};
          s->is_leaf = 0;
          s->count = 0;
          s->parent = NULL;
          for(j = 0; j < {max_children}; ++j) s->children[j] = NULL;
          s->children[0] = target->root;
          target->root->parent = s;
          target->root = s;
          {self.split_child(m.target, "s", "0")};
        }}

        curr = target->root;
        while(!curr->is_leaf) {{
          low = 0;
          high = curr->count;
          while(low < high) {{
            mid = low + (high - low) / 2;
            order_cmp = {self.element.compare(self.element.variable("curr->elements[mid]"), m.element)};
            if(order_cmp < 0) low = mid + 1;
            else high = mid;
          }}
          i = low;
          if(curr->children[i]->count == {max_keys}) {{
            {self.split_child(m.target, "curr", "i")};
            order_cmp = {self.element.compare(self.element.variable("curr->elements[i]"), m.element)};
            if(order_cmp < 0) ++i;
          }}
          curr = curr->children[i];
        }}

        low = 0;
        high = curr->count;
        while(low < high) {{
          mid = low + (high - low) / 2;
          order_cmp = {self.element.compare(self.element.variable("curr->elements[mid]"), m.element)};
          if(order_cmp < 0) low = mid + 1;
          else high = mid;
        }}
        i = low;

        for(j = curr->count; j > i; --j) {{
          {self.element.move(self.element.variable("curr->elements[j]"), self.element.variable("curr->elements[j - 1]"))};
        }}
        {self.element.copy(self.element.variable("curr->elements[i]"), m.element)};
        ++curr->count;
        ++target->size;
        return 1;
      """

    # Insertion of an element whose absence the caller has already verified - moves
    # the source into the node when the element type is movable, sparing the deep
    # copy and admitting the moveable-but-not-copyable elements for the map-level
    # set()/emplace() callers; the descent's duplicate check stays as the
    # whole-entry comparison, which never fires for the pre-verified callers
    with self.method("int", "plant", {"target": inout(self), "element": inout(self.element)}, hidden=True, visibility="internal",
      constraint=lambda: self.element.copyable or self.element.moveable, brief="Plant a verified-absent element into the tree (internal)") as m:
      _insert = self.element.move if self.element.moveable else self.element.copy
      m.code = f"""
        {self.node}* s;
        {self.node}* curr;
        size_t low, high, mid, i, j;
        int order_cmp;
        assert(target);

        if(!target->root) {{
          curr = {self.memory.allocate(self.node)};
          curr->is_leaf = 1;
          curr->count = 1;
          curr->parent = NULL;
          for(j = 0; j < {max_children}; ++j) curr->children[j] = NULL;
          {_insert(self.element.variable("curr->elements[0]"), m.element)};
          target->root = curr;
          target->size = 1;
          return 1;
        }}

        if(target->root->count == {max_keys}) {{
          s = {self.memory.allocate(self.node)};
          s->is_leaf = 0;
          s->count = 0;
          s->parent = NULL;
          for(j = 0; j < {max_children}; ++j) s->children[j] = NULL;
          s->children[0] = target->root;
          target->root->parent = s;
          target->root = s;
          {self.split_child(m.target, "s", "0")};
        }}

        curr = target->root;
        while(!curr->is_leaf) {{
          low = 0;
          high = curr->count;
          while(low < high) {{
            mid = low + (high - low) / 2;
            order_cmp = {self.element.compare(self.element.variable("curr->elements[mid]"), m.element)};
            if(order_cmp < 0) low = mid + 1;
            else high = mid;
          }}
          i = low;
          if(curr->children[i]->count == {max_keys}) {{
            {self.split_child(m.target, "curr", "i")};
            order_cmp = {self.element.compare(self.element.variable("curr->elements[i]"), m.element)};
            if(order_cmp < 0) ++i;
          }}
          curr = curr->children[i];
        }}

        low = 0;
        high = curr->count;
        while(low < high) {{
          mid = low + (high - low) / 2;
          order_cmp = {self.element.compare(self.element.variable("curr->elements[mid]"), m.element)};
          if(order_cmp < 0) low = mid + 1;
          else high = mid;
        }}
        i = low;

        for(j = curr->count; j > i; --j) {{
          {self.element.move(self.element.variable("curr->elements[j]"), self.element.variable("curr->elements[j - 1]"))};
        }}
        {_insert(self.element.variable("curr->elements[i]"), m.element)};
        ++curr->count;
        ++target->size;
        return 1;
      """

    with self.emplace as m:
      create_args = [getattr(m, name) for name in self.element.constructor_parameters]
      _temp_elem = self.element.variable("temp_elem")
      _destroy_temp = f"{self.element.destroy(_temp_elem)};" if self.element.destructible else ""
      m.code = lambda m: f"""
        {_temp_elem.definition};
        {self.node}* s;
        {self.node}* curr;
        size_t low, high, mid, i, j;
        int order_cmp;
        assert(target);

        {self.element.create(_temp_elem, *create_args)};
        if({self.find_view(m.target, _temp_elem)} != NULL) {{
          {_destroy_temp}
          return 0;
        }}

        if(!target->root) {{
          curr = {self.memory.allocate(self.node)};
          curr->is_leaf = 1;
          curr->count = 1;
          curr->parent = NULL;
          for(j = 0; j < {max_children}; ++j) curr->children[j] = NULL;
          {self.element.move(self.element.variable("curr->elements[0]"), _temp_elem)};
          {_destroy_temp}
          target->root = curr;
          target->size = 1;
          return 1;
        }}

        if(target->root->count == {max_keys}) {{
          s = {self.memory.allocate(self.node)};
          s->is_leaf = 0;
          s->count = 0;
          s->parent = NULL;
          for(j = 0; j < {max_children}; ++j) s->children[j] = NULL;
          s->children[0] = target->root;
          target->root->parent = s;
          target->root = s;
          {self.split_child(m.target, "s", "0")};
        }}

        curr = target->root;
        while(!curr->is_leaf) {{
          low = 0;
          high = curr->count;
          while(low < high) {{
            mid = low + (high - low) / 2;
            order_cmp = {self.element.compare(self.element.variable("curr->elements[mid]"), _temp_elem)};
            if(order_cmp < 0) low = mid + 1;
            else high = mid;
          }}
          i = low;
          if(curr->children[i]->count == {max_keys}) {{
            {self.split_child(m.target, "curr", "i")};
            order_cmp = {self.element.compare(self.element.variable("curr->elements[i]"), _temp_elem)};
            if(order_cmp < 0) ++i;
          }}
          curr = curr->children[i];
        }}

        low = 0;
        high = curr->count;
        while(low < high) {{
          mid = low + (high - low) / 2;
          order_cmp = {self.element.compare(self.element.variable("curr->elements[mid]"), _temp_elem)};
          if(order_cmp < 0) low = mid + 1;
          else high = mid;
        }}
        i = low;

        for(j = curr->count; j > i; --j) {{
          {self.element.move(self.element.variable("curr->elements[j]"), self.element.variable("curr->elements[j - 1]"))};
        }}
        {self.element.move(self.element.variable("curr->elements[i]"), _temp_elem)};
        {_destroy_temp}
        ++curr->count;
        ++target->size;
        return 1;
      """

    with self.remove as m:
      destroy_found = f"{self.element.destroy(self.element.variable('node_found->elements[idx_found]'))};" if self.element.destructible else ""
      _destroy_vacated = lambda e: f"{self.element.destroy(self.element.variable(e))};" if self.element.destructible else ""
      m.code = f"""
        {self.node}* node;
        {self.node}* node_found = NULL;
        size_t idx_found = 0;
        {self.node}* curr;
        {self.node}* p;
        {self.node}* left;
        {self.node}* right;
        {self.node}* new_root;
        size_t low, high, mid, j, k;
        int order_cmp;

        assert(target);
        if(target->size == 0) return 0;

        node = target->root;
        while(node) {{
          low = 0;
          high = node->count;
          while(low < high) {{
            mid = low + (high - low) / 2;
            order_cmp = {self.element.compare(self.element.variable("node->elements[mid]"), m.element)};
            if(order_cmp == 0) {{
              node_found = node;
              idx_found = mid;
              break;
            }}
            if(order_cmp < 0) low = mid + 1;
            else high = mid;
          }}
          if(node_found) break;
          if(node->is_leaf) break;
          node = node->children[low];
        }}
        if(!node_found) return 0;

        if(!node_found->is_leaf) {{
          {self.node}* pred_node = node_found->children[idx_found];
          size_t pred_idx;
          while(!pred_node->is_leaf) {{
            pred_node = pred_node->children[pred_node->count];
          }}
          pred_idx = pred_node->count - 1;
          {destroy_found}
          {self.element.move(self.element.variable("node_found->elements[idx_found]"), self.element.variable("pred_node->elements[pred_idx]"))};
          {_destroy_vacated("pred_node->elements[pred_idx]")}
          --pred_node->count;
          curr = pred_node;
        }} else {{
          {destroy_found}
          for(j = idx_found; j + 1 < node_found->count; ++j) {{
            {self.element.move(self.element.variable("node_found->elements[j]"), self.element.variable("node_found->elements[j + 1]"))};
          }}
          --node_found->count;
          /* the vacated top slot coincides with the destroyed one when the removed
             element was last - the shift never ran and the slot is already gone */
          if(idx_found < node_found->count) {{ {_destroy_vacated("node_found->elements[node_found->count]")} }}
          curr = node_found;
        }}

        while(curr != target->root && curr->count < {min_keys}) {{
          p = curr->parent;
          k = 0;
          while(k <= p->count && p->children[k] != curr) ++k;
          assert(k <= p->count);

          /* Case 1: Borrow from left sibling */
          if(k > 0 && p->children[k - 1]->count > {min_keys}) {{
            left = p->children[k - 1];
            for(j = curr->count; j > 0; --j) {{
              {self.element.move(self.element.variable("curr->elements[j]"), self.element.variable("curr->elements[j - 1]"))};
            }}
            if(!curr->is_leaf) {{
              for(j = curr->count + 1; j > 0; --j) {{
                curr->children[j] = curr->children[j - 1];
              }}
              curr->children[0] = left->children[left->count];
              left->children[left->count] = NULL;
              if(curr->children[0]) curr->children[0]->parent = curr;
            }}
            {self.element.move(self.element.variable("curr->elements[0]"), self.element.variable("p->elements[k - 1]"))};
            {self.element.move(self.element.variable("p->elements[k - 1]"), self.element.variable("left->elements[left->count - 1]"))};
            ++curr->count;
            --left->count;
            {_destroy_vacated("left->elements[left->count]")}
            break;
          }}

          /* Case 2: Borrow from right sibling */
          if(k < p->count && p->children[k + 1]->count > {min_keys}) {{
            right = p->children[k + 1];
            {self.element.move(self.element.variable("curr->elements[curr->count]"), self.element.variable("p->elements[k]"))};
            if(!curr->is_leaf) {{
              curr->children[curr->count + 1] = right->children[0];
              right->children[0] = NULL;
              if(curr->children[curr->count + 1]) curr->children[curr->count + 1]->parent = curr;
            }}
            {self.element.move(self.element.variable("p->elements[k]"), self.element.variable("right->elements[0]"))};
            for(j = 0; j + 1 < right->count; ++j) {{
              {self.element.move(self.element.variable("right->elements[j]"), self.element.variable("right->elements[j + 1]"))};
            }}
            if(!right->is_leaf) {{
              for(j = 0; j + 1 <= right->count; ++j) {{
                right->children[j] = right->children[j + 1];
              }}
              right->children[right->count] = NULL;
            }}
            ++curr->count;
            --right->count;
            {_destroy_vacated("right->elements[right->count]")}
            break;
          }}

          /* Case 3: Merge with sibling */
          if(k > 0) {{
            left = p->children[k - 1];
            {self.element.move(self.element.variable("left->elements[left->count]"), self.element.variable("p->elements[k - 1]"))};
            for(j = 0; j < curr->count; ++j) {{
              {self.element.move(self.element.variable("left->elements[left->count + 1 + j]"), self.element.variable("curr->elements[j]"))};
            }}
            if(!curr->is_leaf) {{
              for(j = 0; j <= curr->count; ++j) {{
                left->children[left->count + 1 + j] = curr->children[j];
                curr->children[j] = NULL;
                if(left->children[left->count + 1 + j]) left->children[left->count + 1 + j]->parent = left;
              }}
            }}
            left->count += 1 + curr->count;
            for(j = 0; j < curr->count; ++j) {{
              {_destroy_vacated("curr->elements[j]")}
            }}
            for(j = k - 1; j + 1 < p->count; ++j) {{
              {self.element.move(self.element.variable("p->elements[j]"), self.element.variable("p->elements[j + 1]"))};
            }}
            for(j = k; j < p->count; ++j) {{
              p->children[j] = p->children[j + 1];
            }}
            p->children[p->count] = NULL;
            --p->count;
            {_destroy_vacated("p->elements[p->count]")}
            {self.memory.free("curr")};
            curr = p;
          }} else {{
            right = p->children[k + 1];
            {self.element.move(self.element.variable("curr->elements[curr->count]"), self.element.variable("p->elements[k]"))};
            for(j = 0; j < right->count; ++j) {{
              {self.element.move(self.element.variable("curr->elements[curr->count + 1 + j]"), self.element.variable("right->elements[j]"))};
            }}
            if(!curr->is_leaf) {{
              for(j = 0; j <= right->count; ++j) {{
                curr->children[curr->count + 1 + j] = right->children[j];
                right->children[j] = NULL;
                if(curr->children[curr->count + 1 + j]) curr->children[curr->count + 1 + j]->parent = curr;
              }}
            }}
            curr->count += 1 + right->count;
            for(j = 0; j < right->count; ++j) {{
              {_destroy_vacated("right->elements[j]")}
            }}
            for(j = k; j + 1 < p->count; ++j) {{
              {self.element.move(self.element.variable("p->elements[j]"), self.element.variable("p->elements[j + 1]"))};
            }}
            for(j = k + 1; j < p->count; ++j) {{
              p->children[j] = p->children[j + 1];
            }}
            p->children[p->count] = NULL;
            --p->count;
            {_destroy_vacated("p->elements[p->count]")}
            {self.memory.free("right")};
            curr = p;
          }}
        }}

        if(target->root->count == 0) {{
          if(!target->root->is_leaf) {{
            new_root = target->root->children[0];
            new_root->parent = NULL;
            {self.memory.free("target->root")};
            target->root = new_root;
          }} else {{
            {self.memory.free("target->root")};
            target->root = NULL;
          }}
        }}

        --target->size;
        return 1;
      """

    range = self.range
    r = range.variable("r")

    with self.copy as m:
      m.code = f"""
        {r.definition};
        assert(target);
        assert(source);
        {self.create(m.target)};
        for({r} = {range.new(m.source)}; !{range.empty(r)}; {range.move_front(r)}) {{
          {self.put(m.target, range.front_view(r))};
        }}
      """

    with self.move as m:
      m.code = f"""
        assert(target);
        assert(source);
        target->root = source->root;
        target->size = source->size;
        {self.create(m.source)};
      """

    with self.equal as m:
      m.code = f"""
        {r.definition};
        assert(left);
        assert(right);
        if({self.size(m.left)} == {self.size(m.right)}) {{
          for({r} = {range.new(m.left)}; !{range.empty(r)}; {range.move_front(r)}) {{
            if(!{self.contains(m.right, range.front_view(r))}) return 0;
          }}
          return 1;
        }} else return 0;
      """

    rl = range.variable("left_r")
    rr = range.variable("right_r")

    with self.compare as m:
      m.code = f"""
        {rl.definition};
        {rr.definition};
        int order;
        assert(left);
        assert(right);
        for({rl} = {range.new(m.left)}, {rr} = {range.new(m.right)}; !{range.empty(rl)} && !{range.empty(rr)}; {range.move_front(rl)}, {range.move_front(rr)}) {{
          order = {self.element.compare(range.front_view(rl), range.front_view(rr))};
          if(order) return order;
        }}
        return {range.empty(rl)} ? ({range.empty(rr)} ? 0 : -1) : +1;
      """


  def _render_struct(self, stream, header):
    max_keys = 2 * self.order - 1
    max_children = 2 * self.order
    stream.append(f"""
      /** @private */
      typedef struct {self.node} {self.node};
      /** @private */
      struct {self.node} {{
        {std.size_t} count;
        int is_leaf;
        {self.node}* parent;
        {self.element} elements[{max_keys}];
        {self.node}* children[{max_children}];
      }};
    """)
    super()._render_struct(stream, header)
    stream.append(f"""
      struct {self.name} {{
        {self._node_p} root; /**< @private */
        {std.size_t} size; /**< @private */
      }};
    """)


#
class Range(_Range, Bidirectional):

  brief = "Bidirectional range over the set elements"

  def _render_struct(self, stream, header):
    super()._render_struct(stream, header)
    stream.append(f"""
      struct {self.name} {{
        {Indirection(self.iterable, constant=True)} iterable; /**< @private */
        const {self.iterable.node}* front_node; /**< @private */
        {std.size_t} front_index; /**< @private */
        const {self.iterable.node}* back_node; /**< @private */
        {std.size_t} back_index; /**< @private */
        {std.size_t} remaining; /**< @private */
      }};
    """)

  def __setup__(self):
    super().__setup__()

    front_element = self.iterable.element.variable("target->front_node->elements[target->front_index]")
    back_element = self.iterable.element.variable("target->back_node->elements[target->back_index]")

    with self.method(Callable.Parameter(self), "new", {"iterable": self.iterable}, brief="Create the range spanning the whole set",
      description="""
        Creates the range covering all elements of the set in ascending order.
        The range must not outlive the set and the set must not be modified while the range is traversed.

        @param[in] iterable the set to span
        @return the range covering the whole set
      """) as m:
      result = m.result.variable("result")
      m.inline_code = f"""
        {result.definition};
        assert(iterable);
        result.iterable = iterable;
        result.remaining = iterable->size;
        if(iterable->size == 0) {{
          result.front_node = NULL;
          result.front_index = 0;
          result.back_node = NULL;
          result.back_index = 0;
        }} else {{
          result.front_node = iterable->root;
          while(!result.front_node->is_leaf) {{
            result.front_node = result.front_node->children[0];
          }}
          result.front_index = 0;
          result.back_node = iterable->root;
          while(!result.back_node->is_leaf) {{
            result.back_node = result.back_node->children[result.back_node->count];
          }}
          result.back_index = result.back_node->count - 1;
        }}
        return {result};
      """

    with self.empty as m:
      m.inline_code = """
        assert(target);
        return target->remaining == 0;
      """

    with self.front as m:
      result = m.result.variable("result")
      m.inline_code = f"""
        {result.definition};
        assert(target);
        assert(!{self.empty(m.target)});
        {self.element.copy(result, front_element)};
        return {result};
      """

    with self.front_view as m:
      m.inline_code = f"""
        assert(target);
        assert(!{self.empty(m.target)});
        return {front_element.bind(self.iterable.element.view_type)};
      """

    with self.move_front as m:
      m.code = f"""
        assert(target);
        assert(!{self.empty(m.target)});
        --target->remaining;
        if(target->remaining > 0) {{
          if(!target->front_node->is_leaf) {{
            target->front_node = target->front_node->children[target->front_index + 1];
            while(!target->front_node->is_leaf) {{
              target->front_node = target->front_node->children[0];
            }}
            target->front_index = 0;
          }} else {{
            if(target->front_index + 1 < target->front_node->count) {{
              ++target->front_index;
            }} else {{
              while(target->front_node->parent) {{
                const {self.iterable.node}* p = target->front_node->parent;
                size_t k;
                for(k = 0; k <= p->count; ++k) {{
                  if(p->children[k] == target->front_node) break;
                }}
                if(k < p->count) {{
                  target->front_node = p;
                  target->front_index = k;
                  break;
                }}
                target->front_node = p;
              }}
            }}
          }}
        }}
      """

    with self.back as m:
      result = m.result.variable("result")
      m.inline_code = f"""
        {result.definition};
        assert(target);
        assert(!{self.empty(m.target)});
        {self.element.copy(result, back_element)};
        return {result};
      """

    with self.back_view as m:
      m.inline_code = f"""
        assert(target);
        assert(!{self.empty(m.target)});
        return {back_element.bind(self.iterable.element.view_type)};
      """

    with self.move_back as m:
      m.code = f"""
        assert(target);
        assert(!{self.empty(m.target)});
        --target->remaining;
        if(target->remaining > 0) {{
          if(!target->back_node->is_leaf) {{
            target->back_node = target->back_node->children[target->back_index];
            while(!target->back_node->is_leaf) {{
              target->back_node = target->back_node->children[target->back_node->count];
            }}
            target->back_index = target->back_node->count - 1;
          }} else {{
            if(target->back_index > 0) {{
              --target->back_index;
            }} else {{
              while(target->back_node->parent) {{
                const {self.iterable.node}* p = target->back_node->parent;
                size_t k;
                for(k = 0; k <= p->count; ++k) {{
                  if(p->children[k] == target->back_node) break;
                }}
                if(k > 0) {{
                  target->back_node = p;
                  target->back_index = k - 1;
                  break;
                }}
                target->back_node = p;
              }}
            }}
          }}
        }}
      """
