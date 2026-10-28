import metac.std as std
from metac.hash import Xor
from metac.range import Range
from metac.memory import Manager
from metac.core import Composite, _StructRenderer, _type, enforced, Coerce, Type


#
class _Range(_StructRenderer, Range):

  def __init__(self, iterable, *args, component="range", **kwargs):
    super().__init__(iterable.element, iterable._decorate_component(component, abbreviate=not iterable.public, hidden=not iterable.public), visibility=iterable.visibility, **kwargs)
    self.iterable = iterable
    self.component = component
    iterable.references.add(self)
    self.dependencies.add(iterable)

  # A range is a non-owning cursor whose display name is its own identifier and
  # which belongs to the group of the container it spans
  @property
  def _doxygen_type(self):
    if hasattr(self.iterable, "_doxygen_type"):
      return f"{self.iterable._doxygen_type}::Range"
    return super()._doxygen_type

  def _render_description(self, stream):
    super()._render_description(stream)
    stream.append(f"\n@ingroup {self.iterable.name}\n")
    
  def __setup__(self):
    super().__setup__()
    
    with self.copy as m:
      m.inline_code = f"""
        assert(target);
        assert(source);
        *target = *source;
      """

    with self.move as m:
      m.inline_code = f"""
        assert(target);
        assert(source);
        *target = *source;
      """


# Root abstract protocol for all containers holding entities of the same type
class Container(Composite):

  brief = "Abstract container for entities of the same type"

  @enforced
  def __init__(self, name: str, element: Coerce[Type], *args, memory=Manager(), hasher=Xor(), dependencies=(), **kwargs):
    super().__init__(name, *args, dependencies=(*dependencies, std.assert_h, memory, hasher), **kwargs)
    self.element = _type(element)
    self.memory = memory
    self.hasher = hasher
    self.dependencies.add(self.element)

  def __setup__(self):
    super().__setup__()

    self.method("int", "empty", {"target": self}, brief="Check if the container holds no elements",
      description="""
        Reports whether the container holds no elements at all - the protocol operation
        inherited by every container. Equivalent to `size() == 0` and O(1) for every
        container that tracks the element count incrementally.

        @param[in] target the container to check
        @return non-zero if the container holds no elements
      """)
    
    self.method(std.size_t, "size", {"target": self}, brief="Get the number of elements in the container",
      description="""
        Returns the number of elements currently held by the container - the protocol
        operation inherited by every container. O(1) for every container that tracks
        the count incrementally; O(n) for containers that count on demand.

        @param[in] target the container to measure
        @return the number of elements held by the container
      """)
    
    self.method(self.element.view_type, ("find", "view"), {"target": self, "element": self.element}, constraint=lambda: self.element.comparable, brief="Find element and return constant view",
      description="""
        Finds the element in the container per the container lookup mechanics and returns
        a constant view pointing to it, or NULL if the element is not found.

        @param[in] target the container to search
        @param[in] element the element to look for
        @return constant view of the found element, or NULL if not found
      """)

    with self.method("int", "contains", {"target": self, "element": self.element}, constraint=lambda: self.element.comparable, references=(self.find_view,), brief="Check if the container holds the element",
      description="""
        Looks the element up per the container lookup mechanics without modifying the
        container. The cost matches the underlying implementation: expected O(1) for
        hash-based containers, expected O(log n) for tree-based containers, and O(n)
        for linear containers.

        @param[in] target the container to search
        @param[in] element the element to look for
        @return non-zero if the container holds an element equal to the given one
      """) as m:
      m.inline_code = lambda m: f"""
        assert(target);
        return {self.find_view(m.target, m.element)} != NULL;
      """

  @property
  def copyable(self):
    return self.element.copyable

  @property
  def hashable(self):
    return self.element.hashable

  @property
  def comparable(self):
    return self.element.comparable
