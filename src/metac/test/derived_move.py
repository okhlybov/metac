import metac.core
from metac.core import Composite, _StructRenderer, out


# Composite supplying everything except the move - the move must be derived out of
# the default construction and the swap
class Type(_StructRenderer, Composite):

  brief = "Test composite supplying everything except the move - the move is derived"

  def __setup__(self):
    super().__setup__()
    with self.create as m:
      m.inline_code = "assert(target); target->value = (int*)malloc(sizeof(int)); *target->value = -1;"
    with self.destroy as m:
      m.inline_code = "assert(target); free(target->value);"
    with self.copy as m:
      m.inline_code = "assert(target); assert(source); target->value = (int*)malloc(sizeof(int)); *target->value = *source->value;"
    with self.equal as m:
      m.inline_code = "return *left->value == *right->value;"
    with self.compare as m:
      m.inline_code = "return *left->value == *right->value ? 0 : (*left->value > *right->value ? +1 : -1);"
    with self.hash as m:
      m.inline_code = "return (size_t)*target->value;"

  def _render_struct(self, stream, header):
    super()._render_struct(stream, header)
    stream.append(f"struct {self.name} {{ int* value; }};")


x = metac.test.Type(type := Type("derived_move"))

t1 = type.variable("t1")
t2 = type.variable("t2")


x.setup(f"""
  {t1.definition};
  {type.create(t1)};
""")
x.cleanup(f"""
  {type.destroy(t1)};
  {type.destroy(t2)};
""")

x.unit(f"{type.move}(): derived move leaves the source pristine", f"""
  {t2.definition};
  TEST_TRUE( *t1.value == -1 );
  {type.move(t2, t1)};
  TEST_TRUE( *t2.value == -1 );
  TEST_TRUE( *t1.value == -1 ); /* the moved-from source holds the freshly created shell */
  TEST_TRUE( {type.equal(t1, t2)} );
""")
