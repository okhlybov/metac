from metac.container import Container
from metac.core import inout


# Capability mixin for collections admitting element-identified single-element insertion
# and removal - one of the three addressing schemes (element, position, key) along the
# Indexable/Assignable pair and the Mapping/Multimapping keyed families. Fixed-count
# containers (Array) and specialized or differently-addressed containers (String, the
# map families) simply do not mix this capability in.
class Insertable(Container):

  brief = "Abstract insertable collection - element-identified insertion and removal"

  def __setup__(self):
    super().__setup__()

    self.method("int", "put", {"target": inout(self), "element": self.element}, constraint=lambda: self.element.copyable, brief="Add element to collection",
      description="""
        Adds the element to the collection per the collection semantics.
        Every insertable collection implementation inherits or provides this protocol operation.

        @param[in,out] target the collection to add to
        @param[in] element the element to add
        @return non-zero if the element was added
      """)

    self.method("int", "remove", {"target": inout(self), "element": self.element}, constraint=lambda: self.element.comparable, brief="Remove element from collection if present",
      description="""
        Removes the element when the collection holds an equal one, leaving the collection
        unchanged otherwise. Every insertable collection implementation inherits or provides
        this protocol operation.

        @param[in,out] target the collection to remove from
        @param[in] element the element to remove
        @return non-zero if an element was removed and zero if the collection held no equal element
      """)
