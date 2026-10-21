import metac.test
from metac.core import Composite, _StructRenderer


# The composite defining only the lifecycle: the copy, the equality, the ordering
# and the hashing are derived absent and must be cleanly suppressed - the move is
# derived out of the default construction and the swap
class Type(_StructRenderer, Composite):

  brief = "Test composite defining only the lifecycle - the rest of the operations is derived absent"

  def __setup__(self):
    super().__setup__()
    with self.create as m:
      m.inline_code = "assert(target); target->value = 7;"
    with self.destroy as m:
      m.inline_code = "assert(target);"

  def _render_struct(self, stream, header):
    super()._render_struct(stream, header)
    stream.append(f"struct {self.name} {{ int value; }};")


x = metac.test.Type(type := Type("minimal_composite"))

t1 = type.variable("t1")
t2 = type.variable("t2")


x.setup(f"""
  {t1.definition};
  {t2.definition};
  {type.create(t1)};
  {type.create(t2)};
""")
x.cleanup(f"""
  {type.destroy(t1)};
  {type.destroy(t2)};
""")

x.unit(f"{type.create}(): create the minimal composite", f"""
  TEST_TRUE( t1.value == 7 );
""")

x.unit(f"{type.move}(): derived move leaves the source pristine", f"""
  {type.move(t2, t1)};
  TEST_TRUE( t2.value == 7 );
  TEST_TRUE( t1.value == 7 ); /* the moved-from source holds the freshly created shell */
""")
