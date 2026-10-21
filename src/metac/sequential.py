from metac.hash import XorRot
from metac.traversable import Traversable


# Capability mixin for containers whose elements form an ordered series - the iteration
# order is semantically meaningful and canonical, which makes order-sensitive equality
# well defined (the shared pairwise equal) and pairs with the order-sensitive hasher
# default. Requires a range, hence a Traversable.
class Sequential(Traversable):

  brief = "Abstract sequential container - an ordered series of elements"

  def __init__(self, *args, hasher=XorRot(), **kwargs):
    super().__init__(*args, hasher=hasher, **kwargs)

  def __setup__(self):
    super().__setup__()

    range = self.range
    r = range.variable("r")
    r2 = range.variable("r2")

    # The canonical iteration order makes the pairwise walk a valid equality
    with self.equal as m:
      m.code = lambda m: f"""
        assert(left);
        assert(right);
        if({self.size(m.left)} != {self.size(m.right)}) return 0;
        {r.definition};
        {r2.definition};
        for({r} = {range.new(m.left)}, {r2} = {range.new(m.right)}; !{range.empty(r)} && !{range.empty(r2)}; {range.move_front(r)}, {range.move_front(r2)}) {{
          if(!{self.element.equal(range.front_view(r), range.front_view(r2))}) return 0;
        }}
        return 1;
      """
