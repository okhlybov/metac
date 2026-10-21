import metac.std as std
import metac.set
from metac.ordered import Ordered
from metac.range import Bidirectional
from metac.container import _Range
from metac.random import Randomizer
from metac.core import inout, out, _type, _StructRenderer, Indirection, Callable, Expression


#
class Set(_StructRenderer, metac.set.Set, Ordered):

  brief = "Ordered set of distinct values implemented as a treap - iterates in sorted order"
  
  def __init__(self, *args, randomizer=Randomizer(), dependencies=(), **kwargs):
    super().__init__(*args, dependencies=(*dependencies, randomizer), **kwargs)
    self.node = _type(self._decorate_component("node"))
    self._node_p = Indirection(self.node)
    self.randomizer = randomizer
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

      Implemented as the treap - the randomized binary search tree with the algebraic set operations.
      The closest C++ equivalent is [std::set<>](https://cppreference.com/cpp/container/set).
    """

    node_element = self.element.variable("n->element")
    link_element = self.element.variable("(*link)->element")
    # Node pointer expressions bound to their C side counterparts
    node = Expression(self._node_p, "n")
    node_parent = Expression(self._node_p, "n->parent")
    node_left = Expression(self._node_p, "n->left")
    node_right = Expression(self._node_p, "n->right")

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
            p = n->parent;
            if(p) {{
              if(p->left == n) p->left = NULL; else p->right = NULL;
            }}
            {_destroy};
            {self.memory.free("n")};
            n = p;
          }}
        }}
      """

    with self.method(Indirection(self._node_p), "link", {"target": inout(self), "node": Callable.Parameter(self._node_p)}, hidden=True, visibility="internal", brief="Get link to node (internal)") as m:
      m.code = f"""
        assert(target);
        assert(node);
        if(node->parent) return node->parent->left == node ? &node->parent->left : &node->parent->right;
        return &target->root;
      """

    with self.method(None, ("rotate", "left"), {"link": Callable.Parameter(Indirection(self._node_p))}, hidden=True, visibility="internal", brief="Rotate left at link (internal)") as m:
      m.code = f"""
        {self.node}* n;
        {self.node}* pivot;
        n = *link;
        pivot = n->right;
        n->right = pivot->left;
        if(pivot->left) pivot->left->parent = n;
        pivot->parent = n->parent;
        pivot->left = n;
        n->parent = pivot;
        *link = pivot;
      """

    with self.method(None, ("rotate", "right"), {"link": Callable.Parameter(Indirection(self._node_p))}, hidden=True, visibility="internal", brief="Rotate right at link (internal)") as m:
      m.code = f"""
        {self.node}* n;
        {self.node}* pivot;
        n = *link;
        pivot = n->left;
        n->left = pivot->right;
        if(pivot->right) pivot->right->parent = n;
        pivot->parent = n->parent;
        pivot->right = n;
        n->parent = pivot;
        *link = pivot;
      """

    with self.put as m:
      m.code = f"""
        {self.node}* n;
        {self.node}* parent;
        {Indirection(self._node_p)} link;
        int order;
        assert(target);
        link = &target->root;
        parent = NULL;
        while(*link) {{
          order = {self.element.compare(link_element, m.element)};
          if(order == 0) return 0;
          parent = *link;
          link = order > 0 ? &parent->left : &parent->right;
        }}
        n = {self.memory.allocate(self.node)};
        {self.element.copy(node_element, m.element)};
        n->left = n->right = NULL;
        n->parent = parent;
        *link = n;
        ++target->size;
        while(n->parent && {self.randomizer.priority(node_parent)} < {self.randomizer.priority(node)}) {{
          if(n->parent->right == n) {{
            {self.rotate_left(self.link(m.target, "n->parent"))};
          }} else {{
            {self.rotate_right(self.link(m.target, "n->parent"))};
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
        {Indirection(self._node_p)} link;
        int order;
        assert(target);
        n = {self.memory.allocate(self.node)};
        {self.element.create(node_element, *create_args)};
        link = &target->root;
        parent = NULL;
        while(*link) {{
          order = {self.element.compare(link_element, node_element)};
          if(order == 0) {{
            {_destroy_node}
            {self.memory.free("n")};
            return 0;
          }}
          parent = *link;
          link = order > 0 ? &parent->left : &parent->right;
        }}
        n->left = n->right = NULL;
        n->parent = parent;
        *link = n;
        ++target->size;
        while(n->parent && {self.randomizer.priority(node_parent)} < {self.randomizer.priority(node)}) {{
          if(n->parent->right == n) {{
            {self.rotate_left(self.link(m.target, "n->parent"))};
          }} else {{
            {self.rotate_right(self.link(m.target, "n->parent"))};
          }}
        }}
        return 1;
      """

    with self.remove as m:
      _destroy = self.element.destroy(node_element) if self.element.destructible else str()
      m.code = f"""
        {self.node}* n;
        {self.node}* child;
        int order;
        assert(target);
        n = target->root;
        while(n) {{
          order = {self.element.compare(node_element, m.element)};
          if(order == 0) break;
          n = order > 0 ? n->left : n->right;
        }}
        if(!n) return 0;
        while(n->left && n->right) {{
          if({self.randomizer.priority(node_left)} < {self.randomizer.priority(node_right)}) {{
            {self.rotate_left(self.link(m.target, "n"))};
          }} else {{
            {self.rotate_right(self.link(m.target, "n"))};
          }}
        }}
        child = n->left ? n->left : n->right;
        if(child) child->parent = n->parent;
        *{self.link(m.target, "n")} = child;
        {_destroy};
        {self.memory.free("n")};
        --target->size;
        return 1;
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

    # The treap algebra: the split and the merge node operations give the O(m log(n/m))
    # implementations of the algebraic operations. Both operands are consumed - their nodes
    # are reused without copying and the other set is left empty. The parent links and the
    # element resources are maintained throughout

    with self.method(self._node_p, ("merge", "nodes"), {"left": Callable.Parameter(self._node_p), "right": Callable.Parameter(self._node_p)}, hidden=True, visibility="internal", brief="Merge two node trees (internal)") as m:
      m.code = f"""
        if(!{m.left}) return {m.right};
        if(!{m.right}) return {m.left};
        if({self.randomizer.priority(str(m.left))} > {self.randomizer.priority(str(m.right))}) {{
          {m.left}->right = {self.merge_nodes(f"{m.left}->right", m.right)};
          if({m.left}->right) {m.left}->right->parent = {m.left};
          return {m.left};
        }}
        {m.right}->left = {self.merge_nodes(m.left, f"{m.right}->left")};
        if({m.right}->left) {m.right}->left->parent = {m.right};
        return {m.right};
      """

    with self.method(None, ("split", "nodes"), {"tree": Callable.Parameter(self._node_p), "key": self.element, "left": out(Indirection(self._node_p)), "right": out(Indirection(self._node_p))}, hidden=True, visibility="internal", brief="Split node tree by key (internal)") as m:
      m.code = f"""
        assert({m.left});
        assert({m.right});
        if(!{m.tree}) {{
          *{m.left} = *{m.right} = NULL;
          return;
        }}
        if({self.element.compare(self.element.variable(f"{m.tree}->element"), m.key)} < 0) {{
          {self.split_nodes(f"{m.tree}->right", m.key, f"&{m.tree}->right", m.right)};
          if({m.tree}->right) {m.tree}->right->parent = {m.tree};
          *{m.left} = {m.tree};
        }} else {{
          {self.split_nodes(f"{m.tree}->left", m.key, m.left, f"&{m.tree}->left")};
          if({m.tree}->left) {m.tree}->left->parent = {m.tree};
          *{m.right} = {m.tree};
        }}
      """

    with self.method("int", ("discard", "equal"), {"root": inout(Indirection(self._node_p)), "key": self.element}, hidden=True, visibility="internal", brief="Discard element matching key (internal)") as m:
      destroy_element = str(self.element.destroy(self.element.variable("n->element"))) + ";" if self.element.destructible else str()
      m.code = f"""
        int order;
        {self.node}* n;
        {self.node}* parent;
        {self.node}* merged;
        n = *{m.root};
        parent = NULL;
        while(n) {{
          order = {self.element.compare(self.element.variable("n->element"), m.key)};
          if(order == 0) break;
          parent = n;
          n = order > 0 ? n->left : n->right;
        }}
        if(!n) return 0;
        merged = {self.merge_nodes("n->left", "n->right")};
        if(parent) {{
          if(parent->left == n) parent->left = merged; else parent->right = merged;
          if(merged) merged->parent = parent;
        }} else {{
          *{m.root} = merged;
          if(merged) merged->parent = NULL;
        }}
        {destroy_element}
        {self.memory.free("n")};
        return 1;
      """

    with self.method(None, ("destroy", "root"), {"root": Callable.Parameter(self._node_p)}, hidden=True, visibility="internal", brief="Destroy node tree (internal)") as m:
      destroy_element = str(self.element.destroy(self.element.variable("n->element"))) + ";" if self.element.destructible else str()
      m.code = f"""
        {self.node}* n;
        {self.node}* p;
        if({m.root}) {m.root}->parent = NULL; /* detached trees carry stale root parents */
        n = {m.root};
        while(n) {{
          if(n->left) {{
            n = n->left;
          }} else if(n->right) {{
            n = n->right;
          }} else {{
            p = n->parent;
            if(p) {{
              if(p->left == n) p->left = NULL; else p->right = NULL;
            }}
            {destroy_element}
            {self.memory.free("n")};
            n = p;
          }}
        }}
      """

    with self.method(std.size_t, "count", {"node": Callable.Parameter(self._node_p)}, hidden=True, visibility="internal", brief="Count nodes in tree (internal)") as m:
      m.code = f"""
        if(!{m.node}) return 0;
        return 1 + {self.count(f"{m.node}->left")} + {self.count(f"{m.node}->right")};
      """

    algebra_constraint = lambda: self.algebraic_operations and self.element.copyable and self.element.comparable

    with self.method(self._node_p, ('union', 'nodes'), {"a": Callable.Parameter(self._node_p), "b": Callable.Parameter(self._node_p)}, hidden=True, visibility="internal", constraint=algebra_constraint, brief="Union of two node trees (internal)") as m:
      m.code = lambda m: f"""
        {self.node}* low;
        {self.node}* high;
        int taken;
        if(!{m.a}) {{
          return {m.b};
        }}
        if(!{m.b}) return {m.a};
        if({self.randomizer.priority(str(m.a))} < {self.randomizer.priority(str(m.b))}) {{
          {self.node}* swap = {m.a};
          {m.a} = {m.b};
          {m.b} = swap;
        }}
        {self.split_nodes(m.b, self.element.variable(f"{m.a}->element"), "&low", "&high")};
        taken = {self.discard_equal("&high", self.element.variable(f"{m.a}->element"))};
        {m.a}->left = {self.union_nodes(f"{m.a}->left", "low")};
        {m.a}->right = {self.union_nodes(f"{m.a}->right", "high")};
        if({m.a}->left) {m.a}->left->parent = {m.a};
        if({m.a}->right) {m.a}->right->parent = {m.a};
        return {m.a};
      """

    with self.method(self._node_p, ('intersection', 'nodes'), {"a": Callable.Parameter(self._node_p), "b": Callable.Parameter(self._node_p)}, hidden=True, visibility="internal", constraint=algebra_constraint, brief="Intersect two node trees (internal)") as m:
      m.code = lambda m: f"""
        {self.node}* low;
        {self.node}* high;
        int taken;
        if(!{m.a}) {{
          {self.destroy_root(m.b)};
          return NULL;
        }}
        if(!{m.b}) {{
          {self.destroy_root(m.a)};
          return NULL;
        }}
        if({self.randomizer.priority(str(m.a))} < {self.randomizer.priority(str(m.b))}) {{
          {self.node}* swap = {m.a};
          {m.a} = {m.b};
          {m.b} = swap;
        }}
        {self.split_nodes(m.b, self.element.variable(f"{m.a}->element"), "&low", "&high")};
        taken = {self.discard_equal("&high", self.element.variable(f"{m.a}->element"))};
        {m.a}->left = {self.intersection_nodes(f"{m.a}->left", "low")};
        {m.a}->right = {self.intersection_nodes(f"{m.a}->right", "high")};
        if({m.a}->left) {m.a}->left->parent = {m.a};
        if({m.a}->right) {m.a}->right->parent = {m.a};
        if(taken) return {m.a};
        {self.node}* left_result = {m.a}->left;
        {self.node}* right_result = {m.a}->right;
        {str(self.element.destroy(self.element.variable(f"{m.a}->element"))) + ";" if self.element.destructible else str()}
        {self.memory.free(m.a)};
        return {self.merge_nodes("left_result", "right_result")};
      """

    with self.method(self._node_p, ('difference', 'nodes'), {"a": Callable.Parameter(self._node_p), "b": Callable.Parameter(self._node_p)}, hidden=True, visibility="internal", constraint=algebra_constraint, brief="Difference of two node trees (internal)") as m:
      m.code = lambda m: f"""
        {self.node}* low;
        {self.node}* high;
        int taken;
        if(!{m.a}) {{
          {self.destroy_root(m.b)};
          return NULL;
        }}
        if(!{m.b}) return {m.a};
        /* the difference is asymmetric - the priorities of a govern the recursion */
        {self.split_nodes(m.b, self.element.variable(f"{m.a}->element"), "&low", "&high")};
        taken = {self.discard_equal("&high", self.element.variable(f"{m.a}->element"))};
        {m.a}->left = {self.difference_nodes(f"{m.a}->left", "low")};
        {m.a}->right = {self.difference_nodes(f"{m.a}->right", "high")};
        if({m.a}->left) {m.a}->left->parent = {m.a};
        if({m.a}->right) {m.a}->right->parent = {m.a};
        if(taken) {{
          {self.node}* left_result = {m.a}->left;
          {self.node}* right_result = {m.a}->right;
          {str(self.element.destroy(self.element.variable(f"{m.a}->element"))) + ";" if self.element.destructible else str()}
          {self.memory.free(m.a)};
          return {self.merge_nodes("left_result", "right_result")};
        }}
        return {m.a};
      """

    with self.method(self._node_p, ('symmetric_difference', 'nodes'), {"a": Callable.Parameter(self._node_p), "b": Callable.Parameter(self._node_p)}, hidden=True, visibility="internal", constraint=algebra_constraint, brief="Symmetric difference of two node trees (internal)") as m:
      m.code = lambda m: f"""
        {self.node}* low;
        {self.node}* high;
        int taken;
        if(!{m.a}) {{
          return {m.b};
        }}
        if(!{m.b}) return {m.a};
        if({self.randomizer.priority(str(m.a))} < {self.randomizer.priority(str(m.b))}) {{
          {self.node}* swap = {m.a};
          {m.a} = {m.b};
          {m.b} = swap;
        }}
        {self.split_nodes(m.b, self.element.variable(f"{m.a}->element"), "&low", "&high")};
        taken = {self.discard_equal("&high", self.element.variable(f"{m.a}->element"))};
        {m.a}->left = {self.symmetric_difference_nodes(f"{m.a}->left", "low")};
        {m.a}->right = {self.symmetric_difference_nodes(f"{m.a}->right", "high")};
        if({m.a}->left) {m.a}->left->parent = {m.a};
        if({m.a}->right) {m.a}->right->parent = {m.a};
        if(taken) {{
          {self.node}* left_result = {m.a}->left;
          {self.node}* right_result = {m.a}->right;
          {str(self.element.destroy(self.element.variable(f"{m.a}->element"))) + ";" if self.element.destructible else str()}
          {self.memory.free(m.a)};
          return {self.merge_nodes("left_result", "right_result")};
        }}
        return {m.a};
      """

    # The consuming implementations of the algebraic operations: both operands are merged
    # at the node level and the other set is left empty
    with self.method("int", ("apply", "union"), {"target": inout(self), "other": inout(self)}, constraint=algebra_constraint, optional_group="algebraic_operations", brief="Add all elements from other set",
      description="""
        Merges the two node trees at the node level in expected O(m log(n/m)). The other
        set's nodes are taken over so it is left empty - both operands must be distinct
        objects holding comparable elements.

        @param[in,out] target the set to update
        @param[in,out] other the set of elements to add - it is left empty on return
        @return the number of elements added
      """) as m:
      m.code = lambda m: f"""
        size_t previous;
        assert(target);
        assert({m.other});
        if(target == {m.other}) return 0;
        previous = target->size;
        target->root = {self.union_nodes("target->root", f"{m.other}->root")};
        if(target->root) target->root->parent = NULL;
        {m.other}->root = NULL;
        {m.other}->size = 0;
        target->size = {self.count("target->root")};
        return target->size - previous;
      """

    with self.method("int", ("apply", "difference"), {"target": inout(self), "other": inout(self)}, constraint=algebra_constraint, optional_group="algebraic_operations", brief="Remove all elements found in other set",
      description="""
        Removes the nodes whose elements the other tree holds at the node level in expected
        O(m log(n/m)). The other set's nodes are taken over so it is left empty - both
        operands must be distinct objects holding comparable elements.

        @param[in,out] target the set to update
        @param[in,out] other the set of elements to remove - it is left empty on return
        @return the number of elements removed
      """) as m:
      m.code = lambda m: f"""
        size_t previous;
        assert(target);
        assert({m.other});
        if(target == {m.other}) {{
          previous = target->size;
          {self.destroy(m.target)};
          {self.create(m.target)};
          return previous;
        }}
        previous = target->size;
        target->root = {self.difference_nodes("target->root", f"{m.other}->root")};
        if(target->root) target->root->parent = NULL;
        {m.other}->root = NULL;
        {m.other}->size = 0;
        target->size = {self.count("target->root")};
        return previous - target->size;
      """

    with self.method("int", ("apply", "intersection"), {"target": inout(self), "other": inout(self)}, constraint=algebra_constraint, optional_group="algebraic_operations", brief="Keep only elements also present in other set",
      description="""
        Keeps the nodes whose elements the other tree holds at the node level in expected
        O(m log(n/m)). The other set's nodes are taken over so it is left empty - both
        operands must be distinct objects holding comparable elements.

        @param[in,out] target the set to update
        @param[in,out] other the set of elements to keep - it is left empty on return
        @return the number of elements removed
      """) as m:
      m.code = lambda m: f"""
        size_t previous;
        assert(target);
        assert({m.other});
        if(target == {m.other}) return 0;
        previous = target->size;
        target->root = {self.intersection_nodes("target->root", f"{m.other}->root")};
        if(target->root) target->root->parent = NULL;
        {m.other}->root = NULL;
        {m.other}->size = 0;
        target->size = {self.count("target->root")};
        return previous - target->size;
      """

    with self.method("int", ("apply", "symmetric", "difference"), {"target": inout(self), "other": inout(self)}, constraint=algebra_constraint, optional_group="algebraic_operations", brief="Remove elements in both sets, add elements in only one",
      description="""
        Produces the tree holding the elements present in exactly one of the sets at the
        node level in expected O(m log(n/m)). The other set's nodes are taken over so it
        is left empty - both operands must be distinct objects holding comparable elements.

        @param[in,out] target the set to update
        @param[in,out] other the set to symmetric difference with - it is left empty on return
        @return the number of elements added or removed
      """) as m:
      m.code = lambda m: f"""
        size_t previous, other_size;
        assert(target);
        assert({m.other});
        if(target == {m.other}) {{
          previous = target->size;
          {self.destroy(m.target)};
          {self.create(m.target)};
          return previous;
        }}
        previous = target->size;
        other_size = {m.other}->size;
        target->root = {self.symmetric_difference_nodes("target->root", f"{m.other}->root")};
        if(target->root) target->root->parent = NULL;
        {m.other}->root = NULL;
        {m.other}->size = 0;
        target->size = {self.count("target->root")};
        return other_size; /* every element of the other set is either added or causes a removal */
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
        {self.node}* parent;
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
        Creates the range over the treap descending to the leftmost node so the traversal
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
            p = target->front_node->parent;
            while(p && target->front_node == p->right) {{
              target->front_node = p;
              p = p->parent;
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
            p = target->back_node->parent;
            while(p && target->back_node == p->left) {{
              target->back_node = p;
              p = p->parent;
            }}
            target->back_node = p;
          }}
        }}
      """
