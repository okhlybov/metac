from metac.deque import Deque
from metac.range import Forward
from metac.sequential import Sequential
from metac.insertable import Insertable
from metac.container import _Range
from metac.core import _StructRenderer, Callable, Indirection, inout, enforced


#
class Queue(_StructRenderer, Sequential, Insertable):

  brief = "Ordered FIFO container with back push and front pop"
  
  @enforced
  def _make_deque(self, backend: Sequential & Insertable = Deque):
    return backend(self._decorate_component("deque"), self.element, visibility="internal")

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self._deque = self._make_deque()
    self.dependencies.add(self._deque)
    self.range = Range(self)


  @property
  def orderable(self):
    return False

  def __setup__(self):
    super().__setup__()

    _target = self._deque.variable("target->deque")
    _source = self._deque.variable("source->deque")
    _left = self._deque.variable("left->deque")
    _right = self._deque.variable("right->deque")

    with self.empty as m:
      m.code = f"""
        assert(target);
        return {self._deque.empty(_target)};
      """

    with self.size as m:
      m.code = f"""
        assert(target);
        return {self._deque.size(_target)};
      """

    with self.create as m:
      m.code = f"""
        assert(target);
        {self._deque.create(_target)};
      """

    with self.destroy as m:
      m.code = f"""
        assert(target);
        {self._deque.destroy(_target)};
      """

    with self.copy as m:
      m.code = f"""
        assert(target);
        assert(source);
        {self._deque.copy(_target, _source)};
      """

    with self.move as m:
      m.code = f"""
        assert(target);
        assert(source);
        {self._deque.move(_target, _source)};
      """

    with self.equal as m:
      m.code = f"""
        assert(left);
        assert(right);
        return {self._deque.equal(_left, _right)};
      """

    with self.hash as m:
      m.code = f"""
        assert(target);
        return {self._deque.hash(_target)};
      """

    with self.find_view as m:
      m.code = f"""
        assert(target);
        return {self._deque.find_view(_target, m.element)};
      """

    with self.method(None, "enqueue", {"target": inout(self), "element": self.element}, constraint=lambda: self.element.copyable, brief="Add element to back of queue",
      description="""
        Adds the element at the back of the queue in O(1) so it is yielded last by the
        subsequent `dequeue` operations.

        @param[in,out] target the queue to add to
        @param[in] element the element to add to the back
      """) as m:
      m.code = f"""
        assert(target);
        {self._deque.push_back(_target, m.element)};
      """

    with self.method(None, "emplace", {"target": inout(self)} | self.element.constructor_parameters,
      constraint=lambda: self.element.emplaceable, brief="Construct element in-place at back of queue",
      description="""
        Constructs an element in-place with forwarded parameters at the back of the queue in O(1).

        @param[in,out] target the queue to add to
      """) as m:
      create_args = [getattr(m, name) for name in self.element.constructor_parameters]
      m.code = f"""
        assert(target);
        {self._deque.emplace_back(_target, *create_args)};
      """

    with self.method(self.element, "dequeue", {"target": inout(self)}, constraint=lambda: self.element.moveable, brief="Remove and return element from front of queue",
      description="""
        Removes and moves out the element which has been in the queue the longest in O(1).
        The returned element is a moved copy so the caller owns it.

        @param[in,out] target the queue to remove from - must not be empty
        @return the removed front element
      """) as m:
      m.code = f"""
        assert(target);
        return {self._deque.pop_front(_target)};
      """

    with self.method(self.element, "front", {"target": self}, constraint=lambda: self.element.copyable, brief="Get front element",
      description="""
        Returns a copy of the element to be returned by the next `dequeue` in O(1)
        without modifying the queue.

        @param[in] target the queue to read - must not be empty
        @return the element at the front without removing it
      """) as m:
      m.code = f"""
        assert(target);
        return {self._deque.front(_target)};
      """

    with self.method(self.element, "back", {"target": self}, constraint=lambda: self.element.copyable, brief="Get back element",
      description="""
        Returns a copy of the most recently enqueued element in O(1) without modifying
        the queue.

        @param[in] target the queue to read - must not be empty
        @return the element at the back without removing it
      """) as m:
      m.code = f"""
        assert(target);
        return {self._deque.back(_target)};
      """

    with self.put as m:
      m.inline_code = f"""
        assert(target);
        {self.enqueue(m.target, m.element)};
        return 1;
      """

    with self.remove as m:
      m.code = lambda m: f"""
        assert(target);
        return {self._deque.remove(_target, m.element)};
      """

    self.description = f"""
      Requires the element type (@ref {self.element}) to be *Copyable*.
      Supports one way element traversal via the corresponding @ref {self.range} iterator.

      Implemented as the FIFO adapter over the internal @ref Deque.
      The closest C++ equivalent is [std::queue<>](https://cppreference.com/cpp/container/queue).
    """

  def _render_struct(self, stream, header):
    super()._render_struct(stream, header)
    stream.append(f"""
      struct {self.name} {{
        {self._deque.variable("deque").definition}; /**< @private */
      }};
    """)


#
class Range(_Range, Forward):

  brief = "Forward range over the queue elements"

  def _render_struct(self, stream, header):
    super()._render_struct(stream, header)
    stream.append(f"""
      struct {self.name} {{
        {Indirection(self.iterable, constant=True)} iterable; /**< @private */
        {self.iterable._deque.node}* front; /**< @private */
        {self.iterable._deque.node}* back; /**< @private */
      }};
    """)

  def __setup__(self):
    super().__setup__()

    with self.method(Callable.Parameter(self), "new", {"iterable": self.iterable}, brief="Create the range spanning the whole queue",
      description="""
        Creates the range over the queue elements traversable from the front towards the
        back. The range must not outlive the queue and the queue must not be modified
        while the range is traversed.

        @param[in] iterable the queue to span
        @return the range covering the whole queue
      """) as m:
      result = m.result.variable("result")
      m.inline_code = f"""
        {result.definition};
        assert(iterable);
        result.front = iterable->deque.front;
        result.back = iterable->deque.back;
        return {result};
      """

    with self.empty as m:
      m.inline_code = f"""
        assert(target);
        return !target->front || !target->back || target->front == target->back->next;
      """

    front_element = self.iterable.element.variable("target->front->element")

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
