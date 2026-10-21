from metac.core import inout
from metac.indexable import Indexable


# Capability mixin declaring position-addressed assignment for collections reachable
# by index - the writable half of the Indexable read protocol (assignability implies
# indexability). Multimapping mixes Indexable without Assignable since replacing "the
# element at a key" is ambiguous under duplicate keys.
class Assignable(Indexable):

  def __setup__(self):
    super().__setup__()

    valid_index = lambda: self.index.comparable or self.index.orderable

    self.method(None, "set", {"target": inout(self), "index": self.index, "element": self.element}, constraint=lambda: valid_index() and self.element.copyable, brief="Set the element at index",
      description="""
        Associates the element with the index - either storing it at the brand new entry
        or replacing the contents of the element already held at the index in place.
        The cost matches the underlying implementation: expected O(1) for hash-based and direct-indexed
        containers, expected O(log n) for tree-based containers.

        @param[in,out] target the collection to update
        @param[in] index the index to assign the element at
        @param[in] element the element to store - the element previously held at the index is destroyed
      """)
