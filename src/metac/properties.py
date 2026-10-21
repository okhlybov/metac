from metac.container import Container


# FIXME to be removed
# Base of the property mixins (the -ed family): a property claims a structural invariant
# of the container and, as the requirement application of that claim, enforces the trait
# it demands of its subject at the claiming container's construction time.
# The demand face pairs with the bool trait query face - see _Traitful.
class Property(Container):

  brief = "Abstract property mixin - claims a structural invariant and enforces the trait it demands of its subject"
