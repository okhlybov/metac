from metac.container import Container


# Capability mixin for containers exposing a range over their contents - the
# container-side counterpart of the range-directionality axis (Forward/Bidirectional/
# DirectAccess describe the cursor, Traversable describes the container). Provides the
# traversal-based defaults for the element lookup and hashing: tree-, bucket- and
# strchr-based descendants override find_view with their faster paths.
class Traversable(Container):

  brief = "Abstract traversable container providing range-based lookup and hashing defaults"

  def __setup__(self):
    super().__setup__()

    range = self.range
    r = range.variable("r")

    with self.find_view as m:
      m.code = lambda m: f"""
        {r.definition};
        assert(target);
        for({r} = {range.new(m.target)}; !{range.empty(r)}; {range.move_front(r)}) {{
          if({self.element.equal(range.front_view(r), m.element)}) return {range.front_view(r)};
        }}
        return ({self.element.view_type})NULL;
      """

    with self.hash as m:
      state = self.hasher.state_t.variable("state")
      m.code = lambda m: f"""
        size_t result;
        {r.definition};
        {state.definition};
        assert(target);
        {self.hasher.create(state)};
        for({r} = {range.new(m.target)}; !{range.empty(r)}; {range.move_front(r)}) {{
          {self.hasher.update(state, self.element.hash(range.front_view(r)))};
        }}
        result = {self.hasher.hash(state)};
        {self.hasher.destroy(state)};
        return result;
      """
