import metac.std as std
from metac.core import Composite, _type, inout


#
class Range(Composite):
  
  def __init__(self, element, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.element = _type(element)

  @property
  def swappable(self):
    return False # ranges are non-owning cursors - swapping is indistinguishable from copying

  def __setup__(self):
    super().__setup__()
    self.create = None
    self.destroy = None
    self.swap = None
    self.equal = None
    self.compare = None
    self.hash = None

  @property
  def _iterable_name(self):
    return self.iterable.name if hasattr(self.iterable, "name") else self.iterable


#
class Input(Range):

  brief = "Forward iterator"

  def __setup__(self):
    super().__setup__()
    self.method("int", "empty", {"target": self}, brief="Check if the range is exhausted",
      description="""
        Reports whether the range has no more elements to yield - the mandatory first check
        before reading from or advancing the range.

        @param[in] target the range to test
        @return non-zero if the range is exhausted
      """)
    self.method(self.element, "front", {"target": self}, constraint=lambda: self.element.copyable, brief="Get a copy of the front element",
      description="""
        Returns an owned copy of the element at the current position without moving the
        range - use `front_view` when the copy is not needed.

        @param[in] target the range to read - must not be exhausted
        @return a copy of the element at the front position
      """)
    self.method(self.element.view_type, ("front", "view"), {"target": self}, brief="Get a constant view of the front element",
      description="""
        Returns a pointer to the element at the current position without copying it.
        The view is only guaranteed until the range is advanced since the traversal
        may invalidate the underlying position.

        @param[in] target the range to read - must not be exhausted
        @return a constant view of the element at the front position, valid until the range is advanced
      """)
    self.method(None, ("move", "front"), {"target": inout(self)}, brief="Advance the range to the next element",
      description="""
        Steps the range over to the next element in the traversal direction - the element
        read at the current position is no longer accessible afterwards.

        @param[in,out] target the range to advance - must not be exhausted
      """)


#
class Forward(Input):

  brief = "Forward copyable iterator"

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    
  def __setup__(self):
    super().__setup__()

    self.description = f"""
      This iterator allows traversing the iterable container (@ref {self._iterable_name}) in forward direction.
    """
    

  @property
  def copyable(self):
    return True


#
class Backward(Input):

  brief = "Backward copyable iterator"

  @property
  def copyable(self):
    return True

  def __setup__(self):
    super().__setup__()

    self.description = f"""
      This iterator allows traversing the iterable container (@ref {self._iterable_name}) in backward direction.
    """

    self.method(self.element, "back", {"target": self}, constraint=lambda: self.element.copyable, brief="Get a copy of the back element",
      description="""
        Returns an owned copy of the element at the back position of the traversal - the
        opposite end of the one `front` reads - without moving the range.

        @param[in] target the range to read - must not be exhausted
        @return a copy of the element at the back position
      """)
    self.method(self.element.view_type, ("back", "view"), {"target": self}, brief="Get a constant view of the back element",
      description="""
        Returns a pointer to the element at the back position of the traversal without
        copying it. The view is only guaranteed until the range is retreated.

        @param[in] target the range to read - must not be exhausted
        @return a constant view of the element at the back position, valid until the range is retreated
      """)
    self.method(None, ("move", "back"), {"target": inout(self)}, brief="Retreat the range to the previous element",
      description="""
        Steps the range over to the previous element against the traversal direction -
        the backward counterpart of `move_front`.

        @param[in,out] target the range to retreat - must not be exhausted
      """)


#
class Bidirectional(Forward, Backward):
  
  brief = "Bidirectional (forward/backward) copyable iterator"
  
  def __setup__(self):
    super().__setup__()
    
    self.description = f"""
      This iterator allows traversing the iterable container (@ref {self._iterable_name}) in both (forward and backward) directions.
    """


#
class DirectAccess(Forward, Backward):

  brief = "Bidirectional (forward/backward) copyable iterator with direct access"

  def __setup__(self):
    super().__setup__()

    self.description = f"""
      This iterator allows traversing the iterable container (@ref {self._iterable_name}) in both (forward and backward) directions.
      In addition, it provides a direct (indexed) access to the range of currently accessible range's elements.
    """

    self.method(self.element, "get", {"target": self, "index": std.size_t}, constraint=lambda: self.element.copyable, brief="Get a copy of the element at offset",
      description="""
        Returns an owned copy of the element at the given offset from the current position
        without moving the range - the direct access counterpart of `front`.

        @param[in] target the range to read
        @param[in] index the offset from the current position
        @return a copy of the element at the offset
      """)
    self.method(self.element.view_type, "view", {"target": self,  "index": std.size_t}, brief="Get a constant view of the element at offset",
      description="""
        Returns a pointer to the element at the given offset from the current position
        without copying it. The view is only guaranteed until the range is advanced.

        @param[in] target the range to read
        @param[in] index the offset from the current position
        @return a constant view of the element at the offset, valid until the range is advanced
      """)
    self.method(std.size_t, "size", {"target": self}, brief="Get the number of remaining elements",
      description="""
        Returns how many elements are left between the current position and the back one -
        the distance the repeated `move_front` calls would cover.

        @param[in] target the range to measure
        @return the number of elements left between the current position and the back one
      """)
