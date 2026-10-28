import metac.std as std
import metac.set
from metac.ordered import Ordered
from metac.range import Bidirectional
from metac.container import _Range
from metac.core import inout, _type, _StructRenderer, Indirection, Callable


#
class Set(_StructRenderer, metac.set.Set, Ordered):

  brief = "Ordered set of distinct values implemented as a red-black tree - iterates in sorted order"

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

      Implemented as a red-black tree with strictly bounded height <= 2 * log2(n + 1).
      Node color is encoded directly into the lowest bit of the parent pointer, eliminating struct padding.
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
            p = ({self.node}*)(n->parent & ~(size_t)1);
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
        if(r->left) r->left->parent = ((size_t)n) | (r->left->parent & 1);
        p = ({self.node}*)(n->parent & ~(size_t)1);
        r->parent = ((size_t)p) | (r->parent & 1);
        if(!p) target->root = r;
        else if(n == p->left) p->left = r;
        else p->right = r;
        r->left = n;
        n->parent = ((size_t)r) | (n->parent & 1);
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
        if(l->right) l->right->parent = ((size_t)n) | (l->right->parent & 1);
        p = ({self.node}*)(n->parent & ~(size_t)1);
        l->parent = ((size_t)p) | (l->parent & 1);
        if(!p) target->root = l;
        else if(n == p->left) p->left = l;
        else p->right = l;
        l->right = n;
        n->parent = ((size_t)l) | (n->parent & 1);
      """

    with self.method(None, "transplant", {"target": inout(self), "u": Callable.Parameter(self._node_p), "v": Callable.Parameter(self._node_p)}, hidden=True, visibility="internal", brief="Transplant subtrees (internal)") as m:
      m.code = f"""
        {self.node}* p;
        assert(target);
        assert(u);
        p = ({self.node}*)(u->parent & ~(size_t)1);
        if(!p) target->root = v;
        else if(u == p->left) p->left = v;
        else p->right = v;
        if(v) v->parent = ((size_t)p) | (v->parent & 1);
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

    # Shared bottom-up insertion fixup - the single source of the CLRS rebalancing
    # for both put() and emplace(), which link the fresh red node and delegate here
    with self.method(None, ("rebalance", "insert"), {"target": inout(self), "n": Callable.Parameter(self._node_p)}, hidden=True, visibility="internal", brief="Rebalance after linking the freshly inserted red node (internal)") as m:
      m.code = f"""
        {self.node}* p;
        {self.node}* g;
        {self.node}* u;
        assert(target);
        while(n->parent & ~(size_t)1) {{
          p = ({self.node}*)(n->parent & ~(size_t)1);
          if((p->parent & 1) == 0) break; /* parent is black */
          g = ({self.node}*)(p->parent & ~(size_t)1);
          if(!g) break;
          if(p == g->left) {{
            u = g->right;
            if(u && (u->parent & 1)) {{
              p->parent &= ~(size_t)1; /* black */
              u->parent &= ~(size_t)1; /* black */
              g->parent |= 1;          /* red */
              n = g;
            }} else {{
              if(n == p->right) {{
                n = p;
                {self.rotate_left(m.target, "n")};
                p = ({self.node}*)(n->parent & ~(size_t)1);
                g = ({self.node}*)(p->parent & ~(size_t)1);
              }}
              p->parent &= ~(size_t)1; /* black */
              g->parent |= 1;          /* red */
              {self.rotate_right(m.target, "g")};
            }}
          }} else {{
            u = g->left;
            if(u && (u->parent & 1)) {{
              p->parent &= ~(size_t)1; /* black */
              u->parent &= ~(size_t)1; /* black */
              g->parent |= 1;          /* red */
              n = g;
            }} else {{
              if(n == p->left) {{
                n = p;
                {self.rotate_right(m.target, "n")};
                p = ({self.node}*)(n->parent & ~(size_t)1);
                g = ({self.node}*)(p->parent & ~(size_t)1);
              }}
              p->parent &= ~(size_t)1; /* black */
              g->parent |= 1;          /* red */
              {self.rotate_left(m.target, "g")};
            }}
          }}
        }}
        target->root->parent &= ~(size_t)1; /* root is black */
      """

    with self.put as m:
      m.code = f"""
        {self.node}* n;
        {self.node}* parent;
        {self.node}* curr;
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
        assert(((size_t)n & 1) == 0); /* guard assert: verify allocated node is at least 2-byte aligned for 1-bit color tag */
        {self.element.copy(node_element, m.element)};
        n->left = n->right = NULL;
        n->parent = ((size_t)parent) | 1; /* RED */
        if(!parent) target->root = n;
        else if(order > 0) parent->left = n;
        else parent->right = n;
        ++target->size;
        {self.rebalance_insert(m.target, "n")};
        return 1;
      """

    # Insertion of an element whose absence the caller has already verified (or whose
    # whole-entry equality suffices) - moves the source into the fresh node when the
    # element type is movable, sparing the deep copy and admitting the
    # moveable-but-not-copyable elements for the map-level set()/emplace() callers
    with self.method("int", "plant", {"target": inout(self), "element": inout(self.element)}, hidden=True, visibility="internal",
      constraint=lambda: self.element.copyable or self.element.moveable, brief="Plant a verified-absent element into the tree (internal)") as m:
      _insert = self.element.move if self.element.moveable else self.element.copy
      m.code = f"""
        {self.node}* n;
        {self.node}* parent;
        {self.node}* curr;
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
        assert(((size_t)n & 1) == 0);
        {_insert(node_element, m.element)};
        n->left = n->right = NULL;
        n->parent = ((size_t)parent) | 1; /* RED */
        if(!parent) target->root = n;
        else if(order > 0) parent->left = n;
        else parent->right = n;
        ++target->size;
        {self.rebalance_insert(m.target, "n")};
        return 1;
      """

    with self.emplace as m:
      create_args = [getattr(m, name) for name in self.element.constructor_parameters]
      _destroy_node = f"{self.element.destroy(node_element)};" if self.element.destructible else ""
      m.code = lambda m: f"""
        {self.node}* n;
        {self.node}* parent;
        {self.node}* curr;
        int order = 0;
        assert(target);
        n = {self.memory.allocate(self.node)};
        assert(((size_t)n & 1) == 0);
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
        n->parent = ((size_t)parent) | 1; /* RED */
        if(!parent) target->root = n;
        else if(order > 0) parent->left = n;
        else parent->right = n;
        ++target->size;
        {self.rebalance_insert(m.target, "n")};
        return 1;
      """

    with self.remove as m:
      _destroy_z_element = self.element.destroy(z_element) if self.element.destructible else str()
      m.code = f"""
        {self.node}* z;
        {self.node}* y;
        {self.node}* x;
        {self.node}* x_parent;
        {self.node}* w;
        unsigned char y_original_color;
        int order;
        assert(target);
        z = target->root;
        while(z) {{
          order = {self.element.compare(z_element, m.element)};
          if(order == 0) break;
          z = order > 0 ? z->left : z->right;
        }}
        if(!z) return 0;

        y = z;
        y_original_color = (unsigned char)(y->parent & 1);
        if(!z->left) {{
          x = z->right;
          x_parent = ({self.node}*)(z->parent & ~(size_t)1);
          {self.transplant(m.target, "z", "z->right")};
        }} else if(!z->right) {{
          x = z->left;
          x_parent = ({self.node}*)(z->parent & ~(size_t)1);
          {self.transplant(m.target, "z", "z->left")};
        }} else {{
          y = z->right;
          while(y->left) y = y->left;
          y_original_color = (unsigned char)(y->parent & 1);
          x = y->right;
          if(({self.node}*)(y->parent & ~(size_t)1) == z) {{
            x_parent = y;
          }} else {{
            x_parent = ({self.node}*)(y->parent & ~(size_t)1);
            {self.transplant(m.target, "y", "y->right")};
            y->right = z->right;
            y->right->parent = ((size_t)y) | (y->right->parent & 1);
          }}
          {self.transplant(m.target, "z", "y")};
          y->left = z->left;
          y->left->parent = ((size_t)y) | (y->left->parent & 1);
          y->parent = (y->parent & ~(size_t)1) | (z->parent & 1);
        }}

        {_destroy_z_element};
        {self.memory.free("z")};
        --target->size;

        if(y_original_color == 0) {{
          while(x != target->root && (!x || (x->parent & 1) == 0)) {{
            if(x == x_parent->left) {{
              w = x_parent->right;
              if(w && (w->parent & 1)) {{
                w->parent &= ~(size_t)1;
                x_parent->parent |= 1;
                {self.rotate_left(m.target, "x_parent")};
                w = x_parent->right;
              }}
              if((!w || !w->left || (w->left->parent & 1) == 0) && (!w || !w->right || (w->right->parent & 1) == 0)) {{
                if(w) w->parent |= 1;
                x = x_parent;
                x_parent = ({self.node}*)(x->parent & ~(size_t)1);
              }} else {{
                if(!w || !w->right || (w->right->parent & 1) == 0) {{
                  if(w && w->left) w->left->parent &= ~(size_t)1;
                  if(w) w->parent |= 1;
                  {self.rotate_right(m.target, "w")};
                  w = x_parent->right;
                }}
                if(w) {{
                  w->parent = (w->parent & ~(size_t)1) | (x_parent->parent & 1);
                  if(w->right) w->right->parent &= ~(size_t)1;
                }}
                x_parent->parent &= ~(size_t)1;
                {self.rotate_left(m.target, "x_parent")};
                x = target->root;
                break;
              }}
            }} else {{
              w = x_parent->left;
              if(w && (w->parent & 1)) {{
                w->parent &= ~(size_t)1;
                x_parent->parent |= 1;
                {self.rotate_right(m.target, "x_parent")};
                w = x_parent->left;
              }}
              if((!w || !w->left || (w->left->parent & 1) == 0) && (!w || !w->right || (w->right->parent & 1) == 0)) {{
                if(w) w->parent |= 1;
                x = x_parent;
                x_parent = ({self.node}*)(x->parent & ~(size_t)1);
              }} else {{
                if(!w || !w->left || (w->left->parent & 1) == 0) {{
                  if(w && w->right) w->right->parent &= ~(size_t)1;
                  if(w) w->parent |= 1;
                  {self.rotate_left(m.target, "w")};
                  w = x_parent->left;
                }}
                if(w) {{
                  w->parent = (w->parent & ~(size_t)1) | (x_parent->parent & 1);
                  if(w->left) w->left->parent &= ~(size_t)1;
                }}
                x_parent->parent &= ~(size_t)1;
                {self.rotate_right(m.target, "x_parent")};
                x = target->root;
                break;
              }}
            }}
          }}
          if(x) x->parent &= ~(size_t)1;
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
        {std.size_t} parent; /**< @private high bits: parent pointer; bit 0: color (0: black, 1: red) */
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
        Creates the range over the red-black tree descending to the leftmost node so the traversal
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
            p = ({self.iterable.node}*)(target->front_node->parent & ~(size_t)1);
            while(p && target->front_node == p->right) {{
              target->front_node = p;
              p = ({self.iterable.node}*)(p->parent & ~(size_t)1);
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
            p = ({self.iterable.node}*)(target->back_node->parent & ~(size_t)1);
            while(p && target->back_node == p->left) {{
              target->back_node = p;
              p = ({self.iterable.node}*)(p->parent & ~(size_t)1);
            }}
            target->back_node = p;
          }}
        }}
      """
