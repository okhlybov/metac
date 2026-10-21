import metac.std as std
import metac.set
from metac.ordered import Ordered
from metac.range import Bidirectional
from metac.container import _Range
from metac.core import inout, _type, _StructRenderer, Indirection, Callable


#
class Set(_StructRenderer, metac.set.Set, Ordered):

  brief = "Ordered set of distinct values implemented as an AVL tree - iterates in sorted order"

  def __init__(self, *args, dependencies=(), **kwargs):
    super().__init__(*args, dependencies=(*dependencies, std.size_t), **kwargs)
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

    self.description = f"""
      Requires the element type (@ref {self.element}) to be *Orderable*.
      Supports bidirectional element traversal via the corresponding @ref {self.range} iterator - elements are yielded in sorted order.

      Implemented as an AVL tree with strictly bounded height <= 1.44 * log2(n + 2).
      The balance factor (-1, 0, +1) is encoded directly into the lowest 2 bits of the parent pointer, eliminating struct padding.
      The closest C++ equivalent is [std::set<>](https://cppreference.com/cpp/container/set).
    """

    node_element = self.element.variable("n->element")
    curr_element = self.element.variable("curr->element")
    z_element = self.element.variable("z->element")

    with self.size as m:
      m.inline_code = f"""
        assert(target);
        return target->size;
      """

    with self.empty as m:
      m.inline_code = f"""
        assert(target);
        return target->size == 0;
      """

    with self.create as m:
      m.inline_code = f"""
        assert(target);
        target->root = NULL;
        target->size = 0;
      """

    with self.destroy as m:
      _destroy = self.element.destroy(node_element) if self.element.destructible else str()
      m.code = f"""
        {self.node}* n;
        {self.node}* p;
        assert(target);
        n = target->root;
        while(n) {{
          if(n->left) {{
            n = n->left;
          }} else if(n->right) {{
            n = n->right;
          }} else {{
            p = ({self.node}*)(n->parent & ~(size_t)3);
            if(p) {{
              if(p->left == n) p->left = NULL; else p->right = NULL;
            }}
            {_destroy};
            {self.memory.free("n")};
            n = p;
          }}
        }}
      """

    with self.method(None, ("rotate", "left"), {"target": inout(self), "n": Callable.Parameter(self._node_p)}, hidden=True, visibility="internal", brief="Rotate left (internal)") as m:
      m.code = f"""
        {self.node}* r;
        {self.node}* p;
        assert(target);
        assert(n);
        r = n->right;
        assert(r);
        n->right = r->left;
        if(r->left) r->left->parent = ((size_t)n) | (r->left->parent & 3);
        p = ({self.node}*)(n->parent & ~(size_t)3);
        r->parent = ((size_t)p) | (r->parent & 3);
        if(!p) target->root = r;
        else if(n == p->left) p->left = r;
        else p->right = r;
        r->left = n;
        n->parent = ((size_t)r) | (n->parent & 3);
      """

    with self.method(None, ("rotate", "right"), {"target": inout(self), "n": Callable.Parameter(self._node_p)}, hidden=True, visibility="internal", brief="Rotate right (internal)") as m:
      m.code = f"""
        {self.node}* l;
        {self.node}* p;
        assert(target);
        assert(n);
        l = n->left;
        assert(l);
        n->left = l->right;
        if(l->right) l->right->parent = ((size_t)n) | (l->right->parent & 3);
        p = ({self.node}*)(n->parent & ~(size_t)3);
        l->parent = ((size_t)p) | (l->parent & 3);
        if(!p) target->root = l;
        else if(n == p->left) p->left = l;
        else p->right = l;
        l->right = n;
        n->parent = ((size_t)l) | (n->parent & 3);
      """

    with self.method(None, "transplant", {"target": inout(self), "u": Callable.Parameter(self._node_p), "v": Callable.Parameter(self._node_p)}, hidden=True, visibility="internal", brief="Transplant subtrees (internal)") as m:
      m.code = f"""
        {self.node}* p;
        assert(target);
        assert(u);
        p = ({self.node}*)(u->parent & ~(size_t)3);
        if(!p) target->root = v;
        else if(u == p->left) p->left = v;
        else p->right = v;
        if(v) v->parent = ((size_t)p) | (v->parent & 3);
      """

    with self.find_view as m:
      m.code = f"""
        {self.node}* n;
        int order;
        assert(target);
        n = target->root;
        while(n) {{
          order = {self.element.compare(node_element, m.element)};
          if(order == 0) return {node_element.bind(m.result)};
          n = order > 0 ? n->left : n->right;
        }}
        return ({self.element.view_type})NULL;
      """

    with self.put as m:
      m.code = f"""
        {self.node}* n;
        {self.node}* parent;
        {self.node}* curr;
        {self.node}* p;
        int order = 0;
        assert(target);
        parent = NULL;
        curr = target->root;
        while(curr) {{
          order = {self.element.compare(curr_element, m.element)};
          if(order == 0) return 0;
          parent = curr;
          curr = order > 0 ? curr->left : curr->right;
        }}
        n = {self.memory.allocate(self.node)};
        assert(((size_t)n & 3) == 0); /* guard assert: verify allocated node is at least 4-byte aligned for 2-bit balance tag */
        {self.element.copy(node_element, m.element)};
        n->left = n->right = NULL;
        n->parent = ((size_t)parent) | 0; /* balance factor 0 (balanced) */
        if(!parent) target->root = n;
        else if(order > 0) parent->left = n;
        else parent->right = n;
        ++target->size;

        /* Rebalance: bottom-up balance factor adjustment */
        curr = n;
        p = parent;
        while(p) {{
          int p_bf = (int)(p->parent & 3);
          if(curr == p->left) {{
            if(p_bf == 1) {{
              p->parent = (p->parent & ~(size_t)3) | 0;
              break;
            }} else if(p_bf == 0) {{
              p->parent = (p->parent & ~(size_t)3) | 2;
              curr = p;
              p = ({self.node}*)(p->parent & ~(size_t)3);
            }} else {{
              {self.node}* b = p->left;
              int b_bf = (int)(b->parent & 3);
              if(b_bf == 2) {{
                {self.rotate_right(m.target, "p")};
                p->parent = (p->parent & ~(size_t)3) | 0;
                b->parent = (b->parent & ~(size_t)3) | 0;
              }} else {{
                {self.node}* c = b->right;
                int c_bf = (int)(c->parent & 3);
                {self.rotate_left(m.target, "b")};
                {self.rotate_right(m.target, "p")};
                if(c_bf == 2) {{
                  p->parent = (p->parent & ~(size_t)3) | 1;
                  b->parent = (b->parent & ~(size_t)3) | 0;
                }} else if(c_bf == 1) {{
                  p->parent = (p->parent & ~(size_t)3) | 0;
                  b->parent = (b->parent & ~(size_t)3) | 2;
                }} else {{
                  p->parent = (p->parent & ~(size_t)3) | 0;
                  b->parent = (b->parent & ~(size_t)3) | 0;
                }}
                c->parent = (c->parent & ~(size_t)3) | 0;
              }}
              break;
            }}
          }} else {{
            if(p_bf == 2) {{
              p->parent = (p->parent & ~(size_t)3) | 0;
              break;
            }} else if(p_bf == 0) {{
              p->parent = (p->parent & ~(size_t)3) | 1;
              curr = p;
              p = ({self.node}*)(p->parent & ~(size_t)3);
            }} else {{
              {self.node}* b = p->right;
              int b_bf = (int)(b->parent & 3);
              if(b_bf == 1) {{
                {self.rotate_left(m.target, "p")};
                p->parent = (p->parent & ~(size_t)3) | 0;
                b->parent = (b->parent & ~(size_t)3) | 0;
              }} else {{
                {self.node}* c = b->left;
                int c_bf = (int)(c->parent & 3);
                {self.rotate_right(m.target, "b")};
                {self.rotate_left(m.target, "p")};
                if(c_bf == 1) {{
                  p->parent = (p->parent & ~(size_t)3) | 2;
                  b->parent = (b->parent & ~(size_t)3) | 0;
                }} else if(c_bf == 2) {{
                  p->parent = (p->parent & ~(size_t)3) | 0;
                  b->parent = (b->parent & ~(size_t)3) | 1;
                }} else {{
                  p->parent = (p->parent & ~(size_t)3) | 0;
                  b->parent = (b->parent & ~(size_t)3) | 0;
                }}
                c->parent = (c->parent & ~(size_t)3) | 0;
              }}
              break;
            }}
          }}
        }}
        return 1;
      """

    with self.emplace as m:
      create_args = [getattr(m, name) for name in self.element.constructor_parameters]
      _destroy_node = f"{self.element.destroy(node_element)};" if self.element.destructible else ""
      m.code = lambda m: f"""
        {self.node}* n;
        {self.node}* parent;
        {self.node}* curr;
        {self.node}* p;
        int order = 0;
        assert(target);
        n = {self.memory.allocate(self.node)};
        assert(((size_t)n & 3) == 0);
        {self.element.create(node_element, *create_args)};
        parent = NULL;
        curr = target->root;
        while(curr) {{
          order = {self.element.compare(curr_element, node_element)};
          if(order == 0) {{
            {_destroy_node}
            {self.memory.free("n")};
            return 0;
          }}
          parent = curr;
          curr = order > 0 ? curr->left : curr->right;
        }}
        n->left = n->right = NULL;
        n->parent = ((size_t)parent) | 0;
        if(!parent) target->root = n;
        else if(order > 0) parent->left = n;
        else parent->right = n;
        ++target->size;

        /* Rebalance: bottom-up balance factor adjustment */
        curr = n;
        p = parent;
        while(p) {{
          int p_bf = (int)(p->parent & 3);
          if(curr == p->left) {{
            if(p_bf == 1) {{
              p->parent = (p->parent & ~(size_t)3) | 0;
              break;
            }} else if(p_bf == 0) {{
              p->parent = (p->parent & ~(size_t)3) | 2;
              curr = p;
              p = ({self.node}*)(p->parent & ~(size_t)3);
            }} else {{
              {self.node}* b = p->left;
              int b_bf = (int)(b->parent & 3);
              if(b_bf == 2) {{
                {self.rotate_right(m.target, "p")};
                p->parent = (p->parent & ~(size_t)3) | 0;
                b->parent = (b->parent & ~(size_t)3) | 0;
              }} else {{
                {self.rotate_left(m.target, "b")};
                {self.rotate_right(m.target, "p")};
                {self.node}* c = b->parent & ~(size_t)3 ? ({self.node}*)(b->parent & ~(size_t)3) : target->root;
                int c_bf = (int)(c->parent & 3);
                if(c_bf == 2) {{
                  p->parent = (p->parent & ~(size_t)3) | 1;
                  b->parent = (b->parent & ~(size_t)3) | 0;
                }} else if(c_bf == 1) {{
                  p->parent = (p->parent & ~(size_t)3) | 0;
                  b->parent = (b->parent & ~(size_t)3) | 2;
                }} else {{
                  p->parent = (p->parent & ~(size_t)3) | 0;
                  b->parent = (b->parent & ~(size_t)3) | 0;
                }}
                c->parent = (c->parent & ~(size_t)3) | 0;
              }}
              break;
            }}
          }} else {{
            if(p_bf == 2) {{
              p->parent = (p->parent & ~(size_t)3) | 0;
              break;
            }} else if(p_bf == 0) {{
              p->parent = (p->parent & ~(size_t)3) | 1;
              curr = p;
              p = ({self.node}*)(p->parent & ~(size_t)3);
            }} else {{
              {self.node}* b = p->right;
              int b_bf = (int)(b->parent & 3);
              if(b_bf == 1) {{
                {self.rotate_left(m.target, "p")};
                p->parent = (p->parent & ~(size_t)3) | 0;
                b->parent = (b->parent & ~(size_t)3) | 0;
              }} else {{
                {self.rotate_right(m.target, "b")};
                {self.rotate_left(m.target, "p")};
                {self.node}* c = b->parent & ~(size_t)3 ? ({self.node}*)(b->parent & ~(size_t)3) : target->root;
                int c_bf = (int)(c->parent & 3);
                if(c_bf == 1) {{
                  p->parent = (p->parent & ~(size_t)3) | 2;
                  b->parent = (b->parent & ~(size_t)3) | 0;
                }} else if(c_bf == 2) {{
                  p->parent = (p->parent & ~(size_t)3) | 0;
                  b->parent = (b->parent & ~(size_t)3) | 1;
                }} else {{
                  p->parent = (p->parent & ~(size_t)3) | 0;
                  b->parent = (b->parent & ~(size_t)3) | 0;
                }}
                c->parent = (c->parent & ~(size_t)3) | 0;
              }}
              break;
            }}
          }}
        }}
        return 1;
      """

    with self.remove as m:
      _destroy_z_element = self.element.destroy(z_element) if self.element.destructible else str()
      m.code = f"""
        {self.node}* z;
        {self.node}* y;
        {self.node}* p;
        {self.node}* start_rebalance = NULL;
        int child_was_left = 0;
        int order;
        assert(target);
        z = target->root;
        while(z) {{
          order = {self.element.compare(z_element, m.element)};
          if(order == 0) break;
          z = order > 0 ? z->left : z->right;
        }}
        if(!z) return 0;

        if(!z->left) {{
          start_rebalance = ({self.node}*)(z->parent & ~(size_t)3);
          if(start_rebalance) child_was_left = (z == start_rebalance->left);
          {self.transplant(m.target, "z", "z->right")};
        }} else if(!z->right) {{
          start_rebalance = ({self.node}*)(z->parent & ~(size_t)3);
          if(start_rebalance) child_was_left = (z == start_rebalance->left);
          {self.transplant(m.target, "z", "z->left")};
        }} else {{
          y = z->right;
          while(y->left) y = y->left;
          if(({self.node}*)(y->parent & ~(size_t)3) == z) {{
            start_rebalance = y;
            child_was_left = 0;
          }} else {{
            start_rebalance = ({self.node}*)(y->parent & ~(size_t)3);
            child_was_left = 1;
            {self.transplant(m.target, "y", "y->right")};
            y->right = z->right;
            y->right->parent = ((size_t)y) | (y->right->parent & 3);
          }}
          {self.transplant(m.target, "z", "y")};
          y->left = z->left;
          y->left->parent = ((size_t)y) | (y->left->parent & 3);
          y->parent = (y->parent & ~(size_t)3) | (z->parent & 3);
        }}

        {_destroy_z_element};
        {self.memory.free("z")};
        --target->size;

        p = start_rebalance;
        while(p) {{
          {self.node}* next_p = ({self.node}*)(p->parent & ~(size_t)3);
          int next_child_was_left = next_p ? (p == next_p->left) : 0;
          int p_bf = (int)(p->parent & 3);

          if(child_was_left) {{
            if(p_bf == 2) {{
              p->parent = (p->parent & ~(size_t)3) | 0;
            }} else if(p_bf == 0) {{
              p->parent = (p->parent & ~(size_t)3) | 1;
              break;
            }} else {{
              {self.node}* b = p->right;
              int b_bf = (int)(b->parent & 3);
              if(b_bf == 0) {{
                {self.rotate_left(m.target, "p")};
                p->parent = (p->parent & ~(size_t)3) | 1;
                b->parent = (b->parent & ~(size_t)3) | 2;
                break;
              }} else if(b_bf == 1) {{
                {self.rotate_left(m.target, "p")};
                p->parent = (p->parent & ~(size_t)3) | 0;
                b->parent = (b->parent & ~(size_t)3) | 0;
              }} else {{
                {self.node}* c = b->left;
                int c_bf = (int)(c->parent & 3);
                {self.rotate_right(m.target, "b")};
                {self.rotate_left(m.target, "p")};
                if(c_bf == 1) {{
                  p->parent = (p->parent & ~(size_t)3) | 2;
                  b->parent = (b->parent & ~(size_t)3) | 0;
                }} else if(c_bf == 2) {{
                  p->parent = (p->parent & ~(size_t)3) | 0;
                  b->parent = (b->parent & ~(size_t)3) | 1;
                }} else {{
                  p->parent = (p->parent & ~(size_t)3) | 0;
                  b->parent = (b->parent & ~(size_t)3) | 0;
                }}
                c->parent = (c->parent & ~(size_t)3) | 0;
              }}
            }}
          }} else {{
            if(p_bf == 1) {{
              p->parent = (p->parent & ~(size_t)3) | 0;
            }} else if(p_bf == 0) {{
              p->parent = (p->parent & ~(size_t)3) | 2;
              break;
            }} else {{
              {self.node}* b = p->left;
              int b_bf = (int)(b->parent & 3);
              if(b_bf == 0) {{
                {self.rotate_right(m.target, "p")};
                p->parent = (p->parent & ~(size_t)3) | 2;
                b->parent = (b->parent & ~(size_t)3) | 1;
                break;
              }} else if(b_bf == 2) {{
                {self.rotate_right(m.target, "p")};
                p->parent = (p->parent & ~(size_t)3) | 0;
                b->parent = (b->parent & ~(size_t)3) | 0;
              }} else {{
                {self.node}* c = b->right;
                int c_bf = (int)(c->parent & 3);
                {self.rotate_left(m.target, "b")};
                {self.rotate_right(m.target, "p")};
                if(c_bf == 2) {{
                  p->parent = (p->parent & ~(size_t)3) | 1;
                  b->parent = (b->parent & ~(size_t)3) | 0;
                }} else if(c_bf == 1) {{
                  p->parent = (p->parent & ~(size_t)3) | 0;
                  b->parent = (b->parent & ~(size_t)3) | 2;
                }} else {{
                  p->parent = (p->parent & ~(size_t)3) | 0;
                  b->parent = (b->parent & ~(size_t)3) | 0;
                }}
                c->parent = (c->parent & ~(size_t)3) | 0;
              }}
            }}
          }}
          p = next_p;
          child_was_left = next_child_was_left;
        }}
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
    stream.append(f"""
      /** @private */
      typedef struct {self.node} {self.node};
      /** @private */
      struct {self.node} {{
        {self.element} element;
        {self.node}* left;
        {self.node}* right;
        {std.size_t} parent; /**< @private high bits: parent pointer; bits 0-1: balance factor (0: equal, 1: right-heavy, 2: left-heavy) */
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
        {self.iterable.node}* front_node; /**< @private */
        {self.iterable.node}* back_node; /**< @private */
        {std.size_t} remaining; /**< @private */
      }};
    """)

  def __setup__(self):
    super().__setup__()

    front_element = self.element.variable("target->front_node->element")
    back_element = self.element.variable("target->back_node->element")

    with self.method(Callable.Parameter(self), "new", {"iterable": self.iterable}, brief="Create the range spanning the whole set",
      description="""
        Creates the range over the AVL tree descending to the leftmost node so the traversal
        starts at the smallest element and proceeds in ascending order. The range must not
        outlive the set and the set must not be modified while the range is traversed.

        @param[in] iterable the set to span
        @return the range covering the whole set in ascending order
      """) as m:
      result = m.result.variable("result")
      m.inline_code = f"""
        {result.definition};
        assert(iterable);
        result.iterable = iterable;
        result.remaining = iterable->size;
        if(iterable->size == 0) {{
          result.front_node = NULL;
          result.back_node = NULL;
        }} else {{
          result.front_node = iterable->root;
          while(result.front_node->left) result.front_node = result.front_node->left;
          result.back_node = iterable->root;
          while(result.back_node->right) result.back_node = result.back_node->right;
        }}
        return {result};
      """

    with self.empty as m:
      m.inline_code = f"""
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
        {self.iterable.node}* p;
        assert(target);
        assert(!{self.empty(m.target)});
        --target->remaining;
        if(target->remaining > 0) {{
          if(target->front_node->right) {{
            target->front_node = target->front_node->right;
            while(target->front_node->left) target->front_node = target->front_node->left;
          }} else {{
            p = ({self.iterable.node}*)(target->front_node->parent & ~(size_t)3);
            while(p && target->front_node == p->right) {{
              target->front_node = p;
              p = ({self.iterable.node}*)(p->parent & ~(size_t)3);
            }}
            target->front_node = p;
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
        {self.iterable.node}* p;
        assert(target);
        assert(!{self.empty(m.target)});
        --target->remaining;
        if(target->remaining > 0) {{
          if(target->back_node->left) {{
            target->back_node = target->back_node->left;
            while(target->back_node->right) target->back_node = target->back_node->right;
          }} else {{
            p = ({self.iterable.node}*)(target->back_node->parent & ~(size_t)3);
            while(p && target->back_node == p->left) {{
              target->back_node = p;
              p = ({self.iterable.node}*)(p->parent & ~(size_t)3);
            }}
            target->back_node = p;
          }}
        }}
      """
