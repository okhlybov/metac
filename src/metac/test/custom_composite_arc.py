from metac.reference import Counted
from metac.test import Type as _Type
from metac.test.custom_composite import type

x = _Type(type := Counted(type), name="custom_composite_arc")

t = type.variable("t")
t2 = type.variable("t2")

x.setup(f"""
  {t.definition};
  {t2.definition};
  {type.create(t, 3)};
""")
x.cleanup(f"""
  {type.destroy(t)};
""")

x.unit(f"{type.create}(): create reference with parametrized constructor", f"""
  TEST_EQUAL( *{t}->value, 3 );
""")

x.unit(f"{type.copy}(): copy reference", f"""
  {type.copy(t2, t)};
  *{t}->value = 1;
  TEST_EQUAL( *{t2}->value, 1 );
  {type.destroy(t2)};
""")