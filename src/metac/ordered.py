from metac.core import binder, enforced, Orderable
from metac.properties import Property


# Property mixin for containers whose iteration order is born sorted - the ascending
# element (or index) order is an invariant of the structure itself, not a user-maintained
# state (that is Sortable's regime), so backward traversal is available unconditionally.
# Claimed by the tree and flat sets, and by the map families keyed over them. Unordered
# containers (the hash-based families) do not claim it; their iteration order is layout-
# incidental. Unlike the ability mixins (the -able family) a property is also the shape
# of a requirement: a composite keyed over such a component demands the property of it
# and validates the demand at its own construction time via require(). The property owns
# its invariant: every claiming container has the orderability of its ordering subject
# enforced here, in one place.
class Ordered(Property):

  brief = "Abstract ordered container - iterates in ascending element or index order"

  @binder
  def require(obj, other, *args, **kwargs):
    from metac.core import require
    if obj is Ordered:
      return require(other, obj)
    return require(obj, other)

  @enforced
  def _enforce_ordering(self, subject: Orderable):
    return subject

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self._enforce_ordering(self._ordering())

  def _ordering(self):
    # The ordering subject - the type whose orderability backs the ascending iteration
    # promise. Element-ordered containers take the element; the keyed containers override to their index
    return self.element
