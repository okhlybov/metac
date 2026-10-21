from metac.reference import Raw
from metac.test import Type as _Type


x = _Type(type := Raw("int", name="int_raw"))

t = type.variable("t")
t2 = type.variable("t2")

x.setup(f"""
  {t.definition};
  {t2.definition};
  {type.create(t)};
""")
x.cleanup(f"""
  {type.destroy(t)};
""")

x.unit(f"{type.create}(): default create reference", f"""
  TEST_EQUAL( *{t}, 0 );
""")

x.unit(f"{type.copy}(): copy reference", f"""
  {type.copy(t2, t)};
  *{t} = 1;
  TEST_EQUAL( *{t2}, 1 );
""")
