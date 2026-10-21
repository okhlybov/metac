import metac.std as std
from metac.core import inout, Callable, _StructRenderer, enforced, Type, Comparable, Orderable, Coerce
from metac.traversable import Traversable
from metac.indexable import Indexable


# Pure abstract protocol for multimapping containers associating keys with multiple values
class Multimapping(_StructRenderer, Traversable, Indexable):

  brief = "Abstract associative container mapping keys (indices) to multiple values (elements)"

  @enforced
  def __init__(self, name: str, element: Coerce[Type], index: Coerce[Comparable | Orderable], *args, dependencies=(), **kwargs):
    super().__init__(name, element, index, *args, dependencies=(*dependencies, std.assert_h, std.stdlib_h), **kwargs)
    self.dependencies.add(self.index)

  def _ordering(self):
    # The keyed containers order their indices, not their payload elements
    return self.index

  def _hashing(self):
    # The keyed containers hash their indices, not their payload elements
    return self.index

  def __setup__(self):
    super().__setup__()

    valid_index = lambda: self.index.comparable or self.index.orderable

    self.method(self.element, "get", {"target": self, "index": self.index}, constraint=lambda: valid_index() and self.element.copyable, brief="Get copy of first element with key",
      description="""
        Returns an owned copy of the first element associated with the index. Aborts if the key is absent.

        @param[in] target the multimap to query
        @param[in] index the key to look for
        @return copy of the element
      """)

    self.method("int", "put", {"target": inout(self), "index": self.index, "element": self.element},
      constraint=lambda: valid_index() and self.element.copyable, brief="Insert key-value entry into multimap",
      description="""
        Inserts a new key-value entry into the multimap, preserving duplicate keys.

        @param[in,out] target the multimap to insert into
        @param[in] index the key of the new entry
        @param[in] element the value of the new entry
        @return always non-zero
      """)

    self.method("int", "emplace", {"target": inout(self), "index": self.index} | self.element.constructor_parameters,
      constraint=lambda: valid_index() and self.element.copyable and self.element.emplaceable, brief="Construct element in-place for key",
      description="""
        Constructs the element in-place with the forwarded parameters and inserts a new
        key-value entry into the multimap, preserving duplicate keys.

        @param[in,out] target the multimap to insert into
        @param[in] index the key of the new entry
        @return always non-zero once the entry was inserted
      """)

    self.method("int", "remove", {"target": inout(self), "index": self.index}, constraint=valid_index, brief="Remove one entry with specified key",
      description="""
        Removes one occurrence of an entry with the specified index, if present.

        @param[in,out] target the multimap to modify
        @param[in] index the key to remove
        @return non-zero if an entry was removed, zero if absent
      """)

    self.method(std.size_t, "wipe", {"target": inout(self), "index": self.index}, constraint=valid_index, brief="Remove all entries with specified key",
      description="""
        Removes all entries associated with the specified index from the multimap.

        @param[in,out] target the multimap to modify
        @param[in] index the key to remove
        @return number of entries removed
      """)

    self.method(std.size_t, "count", {"target": self, "index": self.index}, constraint=valid_index, brief="Count entries with key",
      description="""
        Returns the number of entries associated with the specified index.

        @param[in] target the multimap to query
        @param[in] index the key to count
        @return number of matching entries
      """)

    if hasattr(self, "range"):
      self.method(Callable.Parameter(self.range), ("equal", "range"), {"target": self, "index": self.index}, constraint=valid_index, brief="Get range covering all entries with key",
        description="""
          Returns a range spanning all entries with the specified index.
          If the key is absent, an empty range is returned.

          @param[in] target the multimap to search
          @param[in] index the key to search for
          @return range covering all matching entries
        """)
