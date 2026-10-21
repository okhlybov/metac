from metac.test import Type as _Type
from metac.core import Composite, _StructRenderer, out


# Custom composite value type
class Type(_StructRenderer, Composite):

  brief = "Test composite owning a heap allocated integer value"
  
  def __setup__(self):
    super().__setup__()
    
    with self.method(None, "create", {"target": out(self), "value": "int"}, brief="Create the composite owning a copy of the given value") as m:
      m.code = """
        target->value = (int*)malloc(sizeof(int));
        *target->value = value;
      """

    with self.destroy as m:
      m.code = "free(target->value);"

    with self.copy as m:
      m.code = """
        target->value = (int*)malloc(sizeof(int));
        *target->value = *source->value;
      """

    with self.move as m:
      m.code = """
        target->value = source->value;
        source->value = NULL;
      """

    with self.equal as m:
      m.code = "return *left->value == *right->value;"

    with self.compare as m:
      m.code = "return *left->value == *right->value ? 0 : (*left->value > *right->value ? +1 : -1);"
      
    with self.hash as m:
      m.code = "return *target->value;"
    
  def _render_struct(self, stream, header):
    super()._render_struct(stream, header)
    stream.append(f"""
      struct {self.name} {{
        int* value;
      }};
    """)
    

x = _Type(type := Type("custom_composite"))

t = type.variable("t")
t2 = type.variable("t2")


x.setup(f"""
  {t.definition};
  {type.create(t, -1)};
""")
x.cleanup(f"""
  {type.destroy(t)};
""")

x.unit(f"{type.create}(): create value", f"""
""")

x.unit(f"{type.copy}(): copy value", f"""
  {t2.definition};
  {type.copy(t2, t)};
  TEST_TRUE( {type.equal(t2, t)} );
  {type.destroy(t2)};
""")

x.unit(f"{type.move}(): move value", f"""
  {t2.definition};
  {type.move(t2, t)};
  TEST_TRUE( *t2.value == -1 );
  TEST_TRUE( t.value == NULL );
  {type.destroy(t2)};
""")
