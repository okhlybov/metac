import metac.std as std
from metac.range import Forward
from metac.sequential import Sequential
from metac.insertable import Insertable
from metac.container import _Range
from metac.core import inout, _type, Callable, _StructRenderer


#
class List(_StructRenderer, Sequential, Insertable):
  
  brief = "Ordered sequential container with element insertion and removal at the front end"
  
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.node = _type(self._decorate_component("node"))
    self.range = Range(self)

  @property
  def orderable(self):
    return False # TODO

  def __setup__(self):
    super().__setup__()

    self.description = f"""
      Requires the element type (@ref {self.element}) to be *Copyable*.
      Supports one way element traversal via the corresponding @ref {self.range} iterator.

      Implemented as the singly linked list.
      The closest C++ equivalent is [std::forward_list<>](https://cppreference.com/cpp/container/forward_list).
    """
  
    node_element = self.element.variable("node->element")
    front_element = self.element.variable("target->front->element")
    target_element = self.element.variable("target_node->element")
    source_element = self.element.variable("source_node->element")
    
    with self.size as m:
      m.inline_code = f"""
        assert(target);
        return target->size;
      """
    
    with self.empty as m:
      m.inline_code = f"""
        assert(target);
        assert((target->size == 0) == (target->front == NULL));
        return target->size == 0;
      """
    
    with self.create as m:
      m.inline_code = f"""
        assert(target);
        target->front = NULL;
        target->size = 0;
      """
    
    with self.destroy as m:
      m.code = f"""
        {self.node}* node;
        assert(target);
        node = target->front;
        while(node) {{
          {self.node}* _node;
           _node = node;
          {self.element.destroy(node_element) if self.element.destructible else str()};
          node = node->next;
          {self.memory.free("_node")};
        }}
      """
    
    with self.copy as m:
      m.code = lambda m: f"""
        {self.node}* source_node;
        {self.node}** target_tail;
        assert(target);
        assert(source);
        if(target == source) return;
        target->front = NULL;
        target->size = 0;
        target_tail = &target->front;
        for(source_node = source->front; source_node; source_node = source_node->next) {{
          {self.node}* node;
          node = {self.memory.allocate(self.node)};
          {self.element.copy(node_element, self.element.variable("source_node->element"))};
          node->next = NULL;
          *target_tail = node;
          target_tail = &node->next;
          ++target->size;
        }}
      """

    with self.move as m:
      m.code = f"""
        assert(target);
        assert(source);
        target->front = source->front;
        target->size = source->size;
        {self.create(m.source)};
      """

    with self.method(None, ("push", "front"), {"target": inout(self), "element": self.element}, constraint=lambda: self.element.copyable, brief="Add element to front",
      description="""
        Inserts the element at the front in O(1) by allocating a new node and linking it
        before the current front. Other elements are untouched so their addresses stay valid.

        @param[in,out] target the list to add to
        @param[in] element the element to add to the front
      """) as m:
      m.code = f"""
        {self.node}* node;
        assert(target);
        node = {self.memory.allocate(self.node)};
        {self.element.copy(node_element, m.element)};
        node->next = target->front;
        target->front = node;
        ++target->size;
      """

    with self.method(None, ("emplace", "front"), {"target": inout(self)} | self.element.constructor_parameters,
      constraint=lambda: self.element.emplaceable, brief="Construct element in-place at front",
      description="""
        Inserts an element constructed in-place with forwarded parameters at the front in O(1)
        by allocating a new node and linking it before the current front. Other elements are untouched.

        @param[in,out] target the list to add to
      """) as m:
      create_args = [getattr(m, name) for name in self.element.constructor_parameters]
      m.code = f"""
        {self.node}* node;
        assert(target);
        node = {self.memory.allocate(self.node)};
        {self.element.create(node_element, *create_args)};
        node->next = target->front;
        target->front = node;
        ++target->size;
      """
    self.macro("emplace", None, {"target": inout(self)} | self.element.constructor_parameters, lambda target, *args: self.emplace_front(target, *args),
      constraint=lambda: self.element.emplaceable, brief="Construct element in-place at front (synonym for emplace_front)")

    with self.method(self.element, ("pop", "front"), {"target": inout(self)}, constraint=lambda: self.element.moveable, brief="Remove and return element from front",
      description="""
        Moves the front element out and releases its node in O(1). The returned element
        is a moved copy so the caller owns it.

        @param[in,out] target the list to remove from - must not be empty
        @return the removed front element
      """) as m:
      result = m.result.variable("result")
      m.code = f"""
        {self.node}* node;
        {result.definition};
        assert(target);
        assert(!{self.empty(m.target)});
        node = target->front;
        {self.element.move(result, node_element)};
        target->front = node->next;
        {self.memory.free("node")};
        --target->size;
        return {result};
      """

    with self.put as m:
      m.inline_code = f"""
        assert(target);
        {self.push_front(m.target, m.element)};
        return 1;
      """

    with self.remove as m:
      curr_elem = self.element.variable("curr->element")
      destroy_curr = f"{self.element.destroy(curr_elem)};" if self.element.destructible else ""
      m.code = lambda m: f"""
        {self.node}* curr;
        {self.node}* prev;
        assert(target);
        prev = NULL;
        curr = target->front;
        while(curr) {{
          if({self.element.equal(curr_elem, m.element)}) {{
            if(prev) prev->next = curr->next;
            else target->front = curr->next;
            {destroy_curr}
            {self.memory.free("curr")};
            --target->size;
            return 1;
          }}
          prev = curr;
          curr = curr->next;
        }}
        return 0;
      """
    
    with self.method(self.element, "front", {"target": self}, constraint=lambda: self.element.copyable, brief="Get front element",
      description="""
        Returns a copy of the first element in O(1) without modifying the list.

        @param[in] target the list to read - must not be empty
        @return the element at the front
      """) as m:
      result = m.result.variable("result")
      m.inline_code = f"""
        {result.definition};
        assert(target);
        assert(!{self.empty(m.target)});
        {self.element.copy(result, front_element)};
        return {result};
      """

    with self.method(self.element.view_type, ("front", "view"), {"target": self}, brief="Get view of front element",
      description="""
        Returns a pointer to the first element without copying it in O(1). The view is valid
        while that element is held by the list - removing it invalidates the view.

        @param[in] target the list to read - must not be empty
        @return a constant view of the element at the front, valid while the element is held by the list
      """) as m:
      m.inline_code = f"""
        assert(target);
        assert(!{self.empty(m.target)});
        return {front_element.bind(m.result)};
      """


  def _render_struct(self, stream, header):
    stream.append(f"""
      /** @private */
      typedef struct {self.node} {self.node};
      /** @private */
      struct {self.node} {{
        {self.element} element;
        {self.node}* next;
      }};
    """)
    super()._render_struct(stream, header)
    stream.append(f"""
      struct {self.name} {{
        {self.node}* front; /**< @private */
        {std.size_t} size; /**< @private */
      }};
    """)


#
class Range(_Range, Forward):
  
  def _render_struct(self, stream, header):
    super()._render_struct(stream, header)
    stream.append(f"""
      struct {self.name} {{
        {self.iterable.node}* front; /**< @private */
      }};
    """)
    
  def __setup__(self):
    super().__setup__()
    
    with self.method(Callable.Parameter(self), "new", {"iterable" : self.iterable}, brief="Create the range spanning the whole list",
      description="""
        Creates the range over the node chain traversable from front to back. The range
        must not outlive the list and the list must not be modified while the range is traversed.

        @param[in] iterable the list to span
        @return the range covering the whole list
      """) as m:
      result = m.result.variable("result")
      m.inline_code = f"""
        {result.definition};
        assert(iterable);
        result.front = iterable->front;
        return {result};
      """

    with self.empty as m:
      m.inline_code = f"""
        assert(target);
        return !target->front;
      """

    front_element = self.element.variable("target->front->element")
    
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
        return {front_element.bind(m.result)};
      """
    
    with self.move_front as m:
      m.inline_code = f"""
        assert(target);
        assert(!{self.empty(m.target)});
        target->front = target->front->next;
      """
