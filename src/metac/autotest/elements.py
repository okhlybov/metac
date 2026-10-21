# Element-kind fixtures for the programmatic test suite.
#
# An ElementKind bundles everything the concept-test mixins need to work with a
# concrete element type: sample values, the C shape of those values as element
# arguments, kind-appropriate equality assertions and optional locals lifecycle.
# Literal kinds (int, cstring) participate in calls as inline expressions; the
# composite kinds (comp, arc, rec) require declared locals which the mixins
# create via decl() and release via local_destroy().


from metac.core import Composite, _StructRenderer, _type, out
from metac.module import Code
from metac.string import String
from metac.record import Record
from metac.reference import Counted


# Global alive-instance counter backing the comp kind - the leak sentinel
_alive_counter = Code(
  interface="extern int at_alive;",
  implementation="int at_alive = 0;",
)


# Owning composite element type: heap-allocated int value with full value
# semantics and alive-instance accounting in create/copy/destroy
class _Composite(_StructRenderer, Composite):

  def __init__(self, *args, **kwargs):
    super().__init__(*args, dependencies=(_alive_counter,), **kwargs)

  def __setup__(self):
    super().__setup__()

    with self.method(None, "create", {"target": out(self), "value": "int"}) as m:
      m.inline_code = f"""
        assert(target);
        target->value = (int*)malloc(sizeof(int));
        *target->value = value;
        ++at_alive;
      """

    with self.destroy as m:
      m.inline_code = f"""
        assert(target);
        if(target->value) {{
          free(target->value);
          --at_alive;
        }}
      """

    with self.copy as m:
      m.inline_code = f"""
        assert(target);
        assert(source);
        target->value = (int*)malloc(sizeof(int));
        *target->value = *source->value;
        ++at_alive;
      """

    with self.move as m:
      m.inline_code = f"""
        assert(target);
        assert(source);
        target->value = source->value;
        source->value = NULL;
      """

    with self.equal as m:
      m.inline_code = "return *left->value == *right->value;"

    with self.compare as m:
      m.inline_code = "return *left->value == *right->value ? 0 : (*left->value > *right->value ? +1 : -1);"

    with self.hash as m:
      m.inline_code = "return (size_t)*target->value;"

  def _render_struct(self, stream, header):
    super()._render_struct(stream, header)
    stream.append(f"""
      struct {self.name} {{
        int* value;
      }};
    """)


# The single cstring instance shared by the cstring element kind and the record
# text field so the generated module defines the type exactly once
_cstring = String("cstring")


class ElementKind:

  def __init__(self, name, type, values, *, literal, arg, eq, view_obs, assert_call,
               decl=None, local_destroy=None, counter=None, numeric=False):
    # name doubles as the generated container name prefix (int_vector, comp_rb_set)
    self.name = name
    self.type = _type(type)
    self.values = list(values)
    # literal(v) -> C expression of the sample value usable where the element's
    # in-form is expected; None for kinds whose values are not literals
    self.literal = literal
    # arg(var) -> element argument expression for a local variable holding the value
    self.arg = arg
    # eq(a, b) -> C boolean expression comparing two element in-form expressions
    self.eq = eq
    # view_obs(view, index, var) -> C statement asserting the view content equals
    # the sample value with the given index (var = local holding it, if any)
    self.view_obs = view_obs
    # assert_call(call, index, var) -> C statements asserting a call result equals
    # the sample value and releasing the result when it owns resources
    self.assert_call = assert_call
    # decl(var, index) -> C statements defining and constructing a local holding
    # the sample value (None for literal kinds which need no locals)
    self.decl = decl
    # local_destroy(var) -> C statement releasing the local (None when the kind owns nothing)
    self.local_destroy = local_destroy
    # C expression of the alive-instances counter (the leak sentinel), if any
    self.counter = counter
    # numeric kinds admit inline arithmetic oracles (bitmask, sortedness, churn)
    self.numeric = numeric

  @property
  def orderable(self):
    return self.type.orderable

  @property
  def comparable(self):
    return self.type.comparable

  @property
  def destructible(self):
    return self.type.destructible


def _int_literal(v):
  return str(v)


def _int_arg(var):
  return var


def _int_eq(a, b):
  return f"({a} == {b})"


def _cstring_literal(v):
  return f'"{v}"'


def _cstring_arg(var):
  return var


def _cstring_eq(a, b):
  return f"(strcmp({a}, {b}) == 0)"


def _composite_decl(type):
  create = str(type.create)
  def decl(var, index):
    return f"{type} {var}; {create}(&{var}, {index});"
  return decl


def _composite_local_destroy(type):
  destroy = str(type.destroy)
  def local_destroy(var):
    return f"{destroy}(&{var});"
  return local_destroy


def _composite_arg(var):
  return f"&{var}"


def _composite_eq(type):
  equal = str(type.equal)
  def eq(a, b):
    return f"{equal}({a}, {b})"
  return eq


def _composite_view_obs(type):
  equal = str(type.equal)
  def view_obs(view, index, var):
    return f"TEST_TRUE({equal}({view}, &{var}));"
  return view_obs


_composite_type = _Composite("at_composite")

INT = ElementKind(
  "int", "int", [0, 1, 2],
  literal=_int_literal, arg=_int_arg, eq=_int_eq,
  view_obs=lambda view, i, var: f"TEST_EQUAL(*{view}, {[0, 1, 2][i]});",
  assert_call=lambda call, i, var: f"TEST_EQUAL({call}, {[0, 1, 2][i]});",
  numeric=True,
)

CSTRING = ElementKind(
  "cstring", _cstring, ["alpha", "beta", "gamma"],
  literal=_cstring_literal, arg=_cstring_arg, eq=_cstring_eq,
  view_obs=lambda view, i, var: f'TEST_EQUAL_CHARS({view}, "{("alpha", "beta", "gamma")[i]}");',
  assert_call=lambda call, i, var: f'{{ char* _r = {call}; TEST_EQUAL_CHARS(_r, "{("alpha", "beta", "gamma")[i]}"); cstring_free(_r); }}',
)

COMP = ElementKind(
  "comp", _composite_type, [1, 2, 3],
  literal=lambda v: None, arg=_composite_arg,
  eq=_composite_eq(_composite_type), view_obs=_composite_view_obs(_composite_type),
  assert_call=lambda call, index, var: f"{{ at_composite _r = {call}; TEST_TRUE(at_composite_equal(&_r, &{var})); at_composite_destroy(&_r); }}",
  decl=_composite_decl(_composite_type), local_destroy=_composite_local_destroy(_composite_type),
  counter="at_alive",
)

ARC = ElementKind(
  "arc", Counted("int", name="at_int_counted"), [10, 20, 30],
  literal=lambda v: None, arg=lambda var: var,
  eq=lambda a, b: f"(*{a} == *{b})",
  view_obs=lambda view, i, var: f"TEST_EQUAL(*{view}, {[10, 20, 30][i]});",
  # Counted handles are spelled int* - the type name is only a doxygen group
  assert_call=lambda call, i, var: f"{{ int* _r = {call}; TEST_EQUAL(*_r, {[10, 20, 30][i]}); at_int_counted_free(_r); }}",
  decl=lambda var, index: f"int* {var} = 0; {var} = at_int_counted_new(); *{var} = {index};",
  local_destroy=lambda var: f"at_int_counted_free({var});",
)

_record_type = Record("at_record", {"tag": "int", "text": _cstring})

REC = ElementKind(
  "rec", _record_type, [1, 2, 3],
  literal=lambda v: None, arg=_composite_arg,
  eq=_composite_eq(_record_type), view_obs=_composite_view_obs(_record_type),
  assert_call=lambda call, index, var: f"{{ at_record _r = {call}; TEST_TRUE(at_record_equal(&_r, &{var})); at_record_destroy(&_r); }}",
  decl=lambda var, index: f"at_record {var}; at_record_create(&{var}); at_record_set_tag(&{var}, {index});",
  local_destroy=_composite_local_destroy(_record_type),
)

# The curated set of kinds the matrix rows refer to by name
KINDS = {k.name: k for k in (INT, CSTRING, COMP, ARC, REC)}
