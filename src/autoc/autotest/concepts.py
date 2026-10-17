# Concept-test mixins: the emission layer of the programmatic test suite.
#
# Each emit_* function targets one concept of the container hierarchy and emits
# self-contained units (every unit declares, constructs, exercises and destroys
# its own locals inside its own C block) for one concrete container type over
# one element kind. Applicability is decided by isinstance checks against the
# generator's own concept classes plus per-method probing - the mixins adapt to
# whatever trait combination the instantiation actually carries.


from autoc.container import Container
from autoc.indexable import Indexable
from autoc.set import Set as SetConcept
from autoc.mapping import Mapping
from autoc.multiset import Multiset
from autoc.multimapping import Multimapping
from autoc.sortable import Sortable
from autoc.bisectable import Bisectable
from autoc.range import Backward, DirectAccess
from autoc.autotest import active


# Single-element insertion verbs in probe preference order, the matching drain
# verbs and the (fill, drain, ordering) pair table. Ascending sample values make
# the LIFO expectation coincide with max-heap ordering, so the push/pop pair
# covers the priority queue without special casing.
FILL_ATTRS = ("put", "push", "push_back", "push_front", "enqueue")
DRAIN_ATTRS = ("pop", "pop_back", "pop_front", "dequeue")
PAIRS = (
  ("push", "pop", "lifo"),
  ("push_back", "pop_back", "lifo"),
  ("push_front", "pop_front", "lifo"),
  ("enqueue", "dequeue", "fifo"),
  ("push_back", "pop_front", "fifo"),
  ("push_front", "pop_back", "fifo"),
)

# (fill verb, observe verb, expected sample index) - which end the observation
# verbs report after two ascending insertions
OBSERVE = (
  ("push", "top", 1),
  ("push", "back", 1),
  ("push", "front", 0),
  ("push_back", "front", 0),
  ("push_back", "back", 1),
  ("push_front", "front", 1),
  ("push_front", "back", 0),
  ("enqueue", "front", 0),
  ("enqueue", "back", 1),
)


def _first(T, attrs):
  for a in attrs:
    if active(T, a):
      return a
  return None


class Ctx:

  def __init__(self, x, T, ek, key_ek=None):
    self.x, self.T, self.ek = x, T, ek
    # Mappings are keyed containers: ek describes the key kind, INT values are assumed
    self.key_ek = key_ek
    self.t = T.variable("t")
    self.t2 = T.variable("t2")
    if isinstance(T, Mapping):
      self.fill_attr = "set" if active(T, "set") else None
    elif isinstance(T, Multimapping):
      self.fill_attr = "put" if active(T, "put") else None
    else:
      self.fill_attr = _first(T, FILL_ATTRS)
    self.drain_attr = _first(T, DRAIN_ATTRS)

  # Sample-value plumbing -------------------------------------------------

  def earg(self, i):
    ek = self.ek
    lit = ek.literal(ek.values[i])
    return lit if lit is not None else ek.arg(f"e{i}")

  def locs(self, n):
    return " ".join(self.ek.decl(f"e{i}", self.ek.values[i]) for i in range(n)) if self.ek.decl else str()

  def locs_free(self, n):
    return " ".join(self.ek.local_destroy(f"e{i}") for i in range(n)) if self.ek.local_destroy else str()

  # Container lifecycle ---------------------------------------------------

  def construct(self, var=None, capacity="4"):
    var = var or self.t
    if active(self.T, "create"):
      # parametrized constructors (e.g. dynamic circular buffer's create(capacity))
      # are distinguished from the default one by their arity, not their name
      extra = len(getattr(self.T.create, "parameters", {})) - 1
      if extra == 0:
        return str(self.T.create(var))
      if extra == 1:
        return str(self.T.create(var, capacity))
    if active(self.T, "create_capacity"):
      return str(self.T.create_capacity(var, capacity))
    return None

  def destruct(self, var=None):
    # Trivial containers (e.g. static vectors of primitives) disable destroy
    if active(self.T, "destroy"):
      return str(self.T.destroy(var or self.t))
    return str()

  def fill(self, i, var=None):
    T, ek = self.T, self.ek
    var = var or self.t
    if isinstance(T, Mapping):
      s = str(T.set(var, self.earg(i), str(100 + i)))
    elif isinstance(T, Multimapping):
      s = str(T.put(var, self.earg(i), str(100 + i)))
    else:
      s = str(getattr(T, self.fill_attr)(var, self.earg(i)))
    return f"{s};"

  def call(self, attr, *args):
    return str(getattr(self.T, attr)(*args))

  def unit(self, tag, body, nlocs=0):
    construct = self.construct()
    if construct is None:
      return
    head = f"{self.t.definition}; {self.locs(nlocs)}"
    tail = f"{self.destruct()}; {self.locs_free(nlocs)}"
    self.x.unit(tag, f"{head};\n{construct};\n{body}\n{tail}\n")

  def value_unit(self, tag, body, nlocs=0):
    # like unit() but for units managing both t and t2
    c1, c2 = self.construct(), self.construct(self.t2)
    if c1 is None or c2 is None:
      return
    head = f"{self.t.definition}; {self.t2.definition}; {self.locs(nlocs)}"
    tail = f"{self.destruct()}; {self.destruct(self.t2)}; {self.locs_free(nlocs)}"
    self.x.unit(tag, f"{head};\n{c1}; {c2};\n{body}\n{tail}\n")


# --------------------------------------------------------------------------- #
# Value protocol - applies to every type, containers included
# --------------------------------------------------------------------------- #

def emit_value(ctx):
  x, T, ek = ctx.x, ctx.T, ctx.ek
  # Counted references compare by handle so equality-based oracles do not apply
  identity = ek.name == "arc"
  can_fill = ctx.fill_attr is not None

  from autoc.array import Array
  if ctx.construct() is not None:
    body = "TEST_TRUE(%s); TEST_EQUAL(%s, 0);" % (ctx.call("empty", ctx.t), ctx.call("size", ctx.t)) \
      if active(T, "empty") and active(T, "size") and not isinstance(T, Array) else str()
    ctx.unit("create()/destroy(): lifecycle smoke", body)

  if can_fill and active(T, "copy"):
    body = [ctx.fill(0), ctx.fill(1), f"TEST_EQUAL({ctx.call('size', ctx.t)}, 2);",
            f"{T.copy(ctx.t2, ctx.t)};"]
    if active(T, "equal") and not identity:
      body.append(f"TEST_TRUE({ctx.call('equal', ctx.t, ctx.t2)});")
    else:
      body.append(f"TEST_EQUAL({ctx.call('size', ctx.t2)}, 2);")
    if active(T, "equal") and not identity:
      body.append(ctx.fill(2))
      body.append(f"TEST_FALSE({ctx.call('equal', ctx.t, ctx.t2)});")
    ctx.value_unit("copy(): replicate contents", "\n".join(body), nlocs=3)

  if can_fill and active(T, "move"):
    body = [ctx.fill(0), ctx.fill(1), f"{T.move(ctx.t2, ctx.t)};",
            f"TEST_TRUE({ctx.call('empty', ctx.t)});",
            f"TEST_EQUAL({ctx.call('size', ctx.t2)}, 2);"]
    ctx.value_unit("move(): transfer ownership leaving empty source", "\n".join(body), nlocs=2)

  if can_fill and active(T, "swap") and active(T, "size"):
    body = [ctx.fill(0), ctx.fill(1), f"{T.swap(ctx.t, ctx.t2)};",
            f"TEST_EQUAL({ctx.call('size', ctx.t)}, 0);",
            f"TEST_EQUAL({ctx.call('size', ctx.t2)}, 2);"]
    ctx.value_unit("swap(): exchange contents", "\n".join(body), nlocs=2)

  if can_fill and active(T, "hash") and active(T, "equal") and not identity:
    body = [ctx.fill(0), ctx.fill(1), f"{T.copy(ctx.t2, ctx.t)};",
            f"TEST_EQUAL({ctx.call('hash', ctx.t)}, {ctx.call('hash', ctx.t2)});"]
    ctx.value_unit("hash(): equal values hash equally", "\n".join(body), nlocs=2)

  if can_fill and active(T, "compare") and not identity:
    body = [ctx.fill(0), ctx.fill(1), ctx.fill(1, ctx.t2), ctx.fill(2, ctx.t2),
            f"TEST_TRUE({ctx.call('compare', ctx.t, ctx.t2)} < 0);",
            f"TEST_TRUE({ctx.call('compare', ctx.t2, ctx.t)} > 0);",
            f"TEST_EQUAL({ctx.call('compare', ctx.t, ctx.t)}, 0);"]
    ctx.value_unit("compare(): consistent value ordering", "\n".join(body), nlocs=3)

  if can_fill and ek.counter:
    # the sentinel counts both the locals and the container-held copies: after
    # destroying the container only the three locals must remain alive
    body = [ctx.fill(0), ctx.fill(1), ctx.fill(2),
            f"TEST_EQUAL({ek.counter}, 6);",
            f"{ctx.destruct()};",
            f"TEST_EQUAL({ek.counter}, 3);",
            ctx.locs_free(3)]
    x.unit("destroy(): releases every held element",
           f"{ctx.t.definition}; {ctx.locs(3)};\n{ctx.construct()};\n" + "\n".join(body) + "\n")


# --------------------------------------------------------------------------- #
# Container protocol - put/remove/contains/find_view on plain containers
# --------------------------------------------------------------------------- #

def emit_container(ctx):
  x, T, ek = ctx.x, ctx.T, ctx.ek
  a0, a1 = ctx.earg(0), ctx.earg(1)

  if active(T, "put"):
    body = [f"TEST_TRUE({ctx.call('put', ctx.t, a0)});",
            f"TEST_EQUAL({ctx.call('size', ctx.t)}, 1);"]
    if active(T, "contains"):
      body.append(f"TEST_TRUE({ctx.call('contains', ctx.t, a0)});")
    ctx.unit("put(): insert new element", "\n".join(body), nlocs=1)

  if active(T, "put") and isinstance(T, SetConcept):
    body = [f"{ctx.call('put', ctx.t, a0)};",
            f"TEST_FALSE({ctx.call('put', ctx.t, a0)});",
            f"TEST_EQUAL({ctx.call('size', ctx.t)}, 1);"]
    ctx.unit("put(): reject duplicate element", "\n".join(body), nlocs=1)

  if active(T, "remove") and (active(T, "put") or ctx.fill_attr):
    body = [f"{ctx.call('put', ctx.t, a0)};" if active(T, "put") else ctx.fill(0),
            f"TEST_TRUE({ctx.call('remove', ctx.t, a0)});",
            f"TEST_EQUAL({ctx.call('size', ctx.t)}, 0);"]
    if active(T, "contains"):
      body.append(f"TEST_FALSE({ctx.call('contains', ctx.t, a0)});")
    ctx.unit("remove(): remove present element", "\n".join(body), nlocs=1)

  if active(T, "remove"):
    body = [f"TEST_FALSE({ctx.call('remove', ctx.t, a1)});",
            f"TEST_EQUAL({ctx.call('size', ctx.t)}, 0);"]
    ctx.unit("remove(): reject absent element", "\n".join(body), nlocs=2)

  if active(T, "find_view") and (active(T, "put") or ctx.fill_attr):
    view = ctx.call("find_view", ctx.t, a0)
    body = [f"{ctx.call('put', ctx.t, a0)};" if active(T, "put") else ctx.fill(0), f"TEST_NOT_NULL({view});"]
    if not isinstance(T, (Mapping, Multimapping)):
      body.append(ek.view_obs(view, 0, "e0"))
    ctx.unit("find_view(): locate held element", "\n".join(body), nlocs=1)

    missing = ctx.call("find_view", ctx.t, ctx.earg(2))
    ctx.unit("find_view(): NULL for absent element", f"TEST_NULL({missing});", nlocs=3)


# --------------------------------------------------------------------------- #
# Indexed protocol - position-based access
# --------------------------------------------------------------------------- #

def emit_indexed(ctx):
  x, T, ek = ctx.x, ctx.T, ctx.ek

  if not (active(T, "indexed") and active(T, "set") and active(T, "get")):
    return

  def grown_prelude():
    if active(T, "create_size"):
      return f"{T.create_size(ctx.t, '1')};"
    if ctx.fill_attr:
      return ctx.fill(0)
    return None

  prelude = grown_prelude()
  if prelude is None:
    return

  body = [prelude,
          f"TEST_TRUE({ctx.call('indexed', ctx.t, '0')});",
          f"TEST_FALSE({ctx.call('indexed', ctx.t, '1')});"]
  ctx.unit("indexed(): bounds check", "\n".join(body), nlocs=1)

  body = [prelude,
          f"{ctx.call('set', ctx.t, '0', ctx.earg(1))};",
          ek.assert_call(ctx.call("get", ctx.t, "0"), 1, "e1")]
  ctx.unit("set()/get(): roundtrip", "\n".join(body), nlocs=2)

  if active(T, "view"):
    view = ctx.call("view", ctx.t, "0")
    body = [prelude, f"{ctx.call('set', ctx.t, '0', ctx.earg(1))};", ek.view_obs(view, 1, "e1")]
    ctx.unit("view(): observe stored element", "\n".join(body), nlocs=2)


# --------------------------------------------------------------------------- #
# Sequence operations - probe-driven fill/drain/observe ladder
# --------------------------------------------------------------------------- #

def emit_sequence(ctx):
  x, T, ek = ctx.x, ctx.T, ctx.ek

  from autoc.circular_buffer import _CircularBuffer
  for fill_attr, drain_attr, order in PAIRS:
    if not (active(T, fill_attr) and active(T, drain_attr)):
      continue
    # the circular buffer's push/pop pair is a FIFO ring, not a LIFO stack
    if isinstance(T, _CircularBuffer) and (fill_attr, drain_attr) == ("push", "pop"):
      order = "fifo"
    first_out, second_out = (1, 0) if order == "lifo" else (0, 1)
    fill = getattr(T, fill_attr)
    drain = getattr(T, drain_attr)
    body = [f"{fill(ctx.t, ctx.earg(0))};", f"{fill(ctx.t, ctx.earg(1))};",
            f"TEST_EQUAL({ctx.call('size', ctx.t)}, 2);",
            ek.assert_call(str(drain(ctx.t)), first_out, f"e{first_out}"),
            ek.assert_call(str(drain(ctx.t)), second_out, f"e{second_out}"),
            f"TEST_TRUE({ctx.call('empty', ctx.t)});"]
    ctx.unit(f"{fill_attr}_{drain_attr}(): {order} order over two elements", "\n".join(body), nlocs=2)

  for fill_attr, obs_attr, expected in OBSERVE:
    view_attr = f"{obs_attr}_view"
    if not active(T, fill_attr):
      continue
    fill = getattr(T, fill_attr)
    if active(T, obs_attr):
      obs = getattr(T, obs_attr)
      body = [f"{fill(ctx.t, ctx.earg(0))};", f"{fill(ctx.t, ctx.earg(1))};",
              ek.assert_call(str(obs(ctx.t)), expected, f"e{expected}")]
      ctx.unit(f"{obs_attr}(): observe after {fill_attr}", "\n".join(body), nlocs=2)
    if active(T, view_attr):
      obs = getattr(T, view_attr)
      body = [f"{fill(ctx.t, ctx.earg(0))};", f"{fill(ctx.t, ctx.earg(1))};",
              ek.view_obs(str(obs(ctx.t)), expected, f"e{expected}")]
      ctx.unit(f"{view_attr}(): observe view after {fill_attr}", "\n".join(body), nlocs=2)

  if active(T, "create_size") and not isinstance(T, SetConcept):
    body = [f"{T.create_size(ctx.t, '3')};",
            f"TEST_EQUAL({ctx.call('size', ctx.t)}, 3);"]
    ctx.unit("create_size(): preallocated construction", "\n".join(body))

  if active(T, "resize") and not isinstance(T, SetConcept):
    body = [f"{T.resize(ctx.t, '2')};", f"TEST_EQUAL({ctx.call('size', ctx.t)}, 2);",
            f"{T.resize(ctx.t, '1')};", f"TEST_EQUAL({ctx.call('size', ctx.t)}, 1);"]
    ctx.unit("resize(): grow and shrink", "\n".join(body))

  if active(T, "capacity") and active(T, "size"):
    body = [f"TEST_TRUE({ctx.call('capacity', ctx.t)} >= {ctx.call('size', ctx.t)});"]
    ctx.unit("capacity(): room for held elements", "\n".join(body))

  if active(T, "clear") and ctx.fill_attr:
    body = [ctx.fill(0), ctx.fill(1), f"{T.clear(ctx.t)};",
            f"TEST_TRUE({ctx.call('empty', ctx.t)});"]
    ctx.unit("clear(): drop all elements", "\n".join(body), nlocs=2)

  if active(T, "full"):
    body = [f"TEST_FALSE({ctx.call('full', ctx.t)});"]
    ctx.unit("full(): fresh container is not full", "\n".join(body))


# --------------------------------------------------------------------------- #
# Set concept - membership semantics, traversal multiplicity, algebra
# --------------------------------------------------------------------------- #

def emit_set(ctx):
  x, T, ek = ctx.x, ctx.T, ctx.ek
  a0, a1, a2 = ctx.earg(0), ctx.earg(1), ctx.earg(2)

  if active(T, "emplace") and getattr(ek.type, "constructor_parameters", None):
    ctor_args = [str(7) for _ in ek.type.constructor_parameters]
    emplaced = ctx.call("emplace", ctx.t, *ctor_args)
    body = [f"TEST_TRUE({emplaced});",
            f"TEST_FALSE({emplaced});"]
    ctx.unit("emplace(): construct in place and reject duplicate", "\n".join(body))

  # Traversal multiplicity: every held element visited exactly once
  if ctx.fill_attr and getattr(T, "range", None) is not None:
    r = T.range.variable("r")
    walk = f"for({r} = {T.range.new(ctx.t)}; !{T.range.empty(r)}; {T.range.move_front(r)})"
    count_body = [ctx.fill(0), ctx.fill(1), ctx.fill(2),
                  "size_t n = 0;",
                  f"{r.definition}; {walk} {{ ++n; }}",
                  f"TEST_EQUAL(n, 3);"]
    ctx.unit("range(): traverse all elements exactly once", "\n".join(count_body), nlocs=3)

    if ek.numeric:
      mask_body = [ctx.fill(0), ctx.fill(1), ctx.fill(2),
                   "unsigned mask = 0;",
                   f"{r.definition}; {walk} {{ mask |= 1u << {T.range.front(r)}; }}",
                   "TEST_EQUAL(mask, 0x7);"]
      ctx.unit("range(): visit each distinct element", "\n".join(mask_body), nlocs=3)

    if ek.numeric and T.orderable:
      sorted_body = [ctx.fill(0), ctx.fill(2), ctx.fill(1),
                     "int prev = -1; size_t n = 0;",
                     f"{r.definition}; {walk} {{ int v = {T.range.front(r)}; TEST_TRUE(prev < v); prev = v; ++n; }}",
                     "TEST_EQUAL(n, 3);"]
      ctx.unit("range(): ordered traversal", "\n".join(sorted_body), nlocs=3)

  # Churn: repeated scatter/gather must not lose or duplicate elements
  if ek.numeric and active(T, "put") and active(T, "remove") and active(T, "contains"):
    i = "i"
    churn = [f"for(size_t {i} = 0; {i} < 100; ++{i}) {ctx.call('put', ctx.t, f'({i}*37) % 100')};",
             f"TEST_EQUAL({ctx.call('size', ctx.t)}, 100);",
             f"for(size_t {i} = 0; {i} < 100; ++{i}) TEST_TRUE({ctx.call('contains', ctx.t, f'({i}*37) % 100')});",
             f"for(size_t {i} = 0; {i} < 100; ++{i}) TEST_TRUE({ctx.call('remove', ctx.t, f'({i}*37) % 100')});",
             f"TEST_TRUE({ctx.call('empty', ctx.t)});"]
    ctx.unit("put()/remove(): churn without loss", "\n".join(churn))

  # Algebraic operations - each unit starts from freshly filled operands and
  # only runs when the particular operation is active for this instantiation
  other = T.variable("other")

  def op_unit(name, op_attr, tfill, ofill, result, asserts):
    lines = [f"{other.definition}; {T.create(other)};"]
    lines += [ctx.fill(i) for i in tfill]
    lines += [f"{getattr(T, f_)(other, ctx.earg(i))};" for f_, i in ofill]
    lines.append(result)
    lines += asserts
    lines.append(f"{T.destroy(other)};")
    ctx.unit(name, "\n".join(lines), nlocs=3)

  if active(T, "apply_union"):
    op_unit("apply_union(): add missing elements", "apply_union", (0, 1), (("put", 1), ("put", 2)),
            f"TEST_EQUAL({T.apply_union(ctx.t, other)}, 1);",
            [f"TEST_EQUAL({ctx.call('size', ctx.t)}, 3);",
             f"TEST_TRUE({ctx.call('contains', ctx.t, a2)});"])
  if active(T, "apply_difference"):
    op_unit("apply_difference(): drop shared elements", "apply_difference", (0, 1, 2), (("put", 1),),
            f"TEST_EQUAL({T.apply_difference(ctx.t, other)}, 1);",
            [f"TEST_EQUAL({ctx.call('size', ctx.t)}, 2);",
             f"TEST_FALSE({ctx.call('contains', ctx.t, a1)});"])
  if active(T, "apply_intersection"):
    op_unit("apply_intersection(): keep shared elements", "apply_intersection", (0, 1), (("put", 1), ("put", 2)),
            f"TEST_EQUAL({T.apply_intersection(ctx.t, other)}, 1);",
            [f"TEST_EQUAL({ctx.call('size', ctx.t)}, 1);",
             f"TEST_TRUE({ctx.call('contains', ctx.t, a1)});"])
  if active(T, "apply_symmetric_difference"):
    op_unit("apply_symmetric_difference(): keep unshared elements", "apply_symmetric_difference", (0, 1), (("put", 1), ("put", 2)),
            f"TEST_EQUAL({T.apply_symmetric_difference(ctx.t, other)}, 2);",
            [f"TEST_TRUE({ctx.call('contains', ctx.t, a0)});",
             f"TEST_TRUE({ctx.call('contains', ctx.t, a2)});",
             f"TEST_FALSE({ctx.call('contains', ctx.t, a1)});"])

  result_set = T.variable("result_set")

  def create_op_unit(name, op_attr, tfill, ofill, call_stmt, asserts):
    lines = [f"{other.definition}; {T.create(other)};",
             f"{result_set.definition};"]
    lines += [ctx.fill(i) for i in tfill]
    lines += [f"{getattr(T, f_)(other, ctx.earg(i))};" for f_, i in ofill]
    lines.append(call_stmt)
    lines += asserts
    lines.append(f"TEST_EQUAL({ctx.call('size', ctx.t)}, {len(tfill)});")
    lines.append(f"TEST_EQUAL({ctx.call('size', other)}, {len(ofill)});")
    lines.append(f"{T.destroy(result_set)};")
    lines.append(f"{T.destroy(other)};")
    ctx.unit(name, "\n".join(lines), nlocs=3)

  if active(T, "create_union"):
    create_op_unit("create_union(): construct union from immutable sources", "create_union", (0, 1), (("put", 1), ("put", 2)),
                   f"{T.create_union(result_set, ctx.t, other)};",
                   [f"TEST_EQUAL({ctx.call('size', result_set)}, 3);",
                    f"TEST_TRUE({ctx.call('contains', result_set, a0)});",
                    f"TEST_TRUE({ctx.call('contains', result_set, a1)});",
                    f"TEST_TRUE({ctx.call('contains', result_set, a2)});"])
  if active(T, "create_difference"):
    create_op_unit("create_difference(): construct difference from immutable sources", "create_difference", (0, 1, 2), (("put", 1),),
                   f"{T.create_difference(result_set, ctx.t, other)};",
                   [f"TEST_EQUAL({ctx.call('size', result_set)}, 2);",
                    f"TEST_TRUE({ctx.call('contains', result_set, a0)});",
                    f"TEST_TRUE({ctx.call('contains', result_set, a2)});",
                    f"TEST_FALSE({ctx.call('contains', result_set, a1)});"])
  if active(T, "create_intersection"):
    create_op_unit("create_intersection(): construct intersection from immutable sources", "create_intersection", (0, 1), (("put", 1), ("put", 2)),
                   f"{T.create_intersection(result_set, ctx.t, other)};",
                   [f"TEST_EQUAL({ctx.call('size', result_set)}, 1);",
                    f"TEST_TRUE({ctx.call('contains', result_set, a1)});",
                    f"TEST_FALSE({ctx.call('contains', result_set, a0)});",
                    f"TEST_FALSE({ctx.call('contains', result_set, a2)});"])
  if active(T, "create_symmetric_difference"):
    create_op_unit("create_symmetric_difference(): construct symmetric difference from immutable sources", "create_symmetric_difference", (0, 1), (("put", 1), ("put", 2)),
                   f"{T.create_symmetric_difference(result_set, ctx.t, other)};",
                   [f"TEST_EQUAL({ctx.call('size', result_set)}, 2);",
                    f"TEST_TRUE({ctx.call('contains', result_set, a0)});",
                    f"TEST_TRUE({ctx.call('contains', result_set, a2)});",
                    f"TEST_FALSE({ctx.call('contains', result_set, a1)});"])
  if active(T, "is_subset"):
    op_unit("is_subset()/is_superset(): subset relation", "is_subset", (0,), (("put", 0), ("put", 1)),
            f"TEST_TRUE({T.is_subset(ctx.t, other)});",
            [f"TEST_TRUE({T.is_superset(other, ctx.t)});"])
    op_unit("is_subset()/is_superset(): non-subset relation", "is_subset", (0, 1), (("put", 0),),
            f"TEST_FALSE({T.is_subset(ctx.t, other)});",
            [f"TEST_FALSE({T.is_superset(other, ctx.t)});"])


# --------------------------------------------------------------------------- #
# Mapping concept - key/value semantics
# --------------------------------------------------------------------------- #

def emit_mapping(ctx):
  x, T, ek = ctx.x, ctx.T, ctx.ek
  k0, k1, k2 = ctx.earg(0), ctx.earg(1), ctx.earg(2)

  if not active(T, "set"):
    return

  ctx.unit("set(): bind new key",
           "\n".join([f"{T.set(ctx.t, k0, '100')};",
                      f"TEST_EQUAL({ctx.call('size', ctx.t)}, 1);",
                      f"TEST_EQUAL({ctx.call('get', ctx.t, k0)}, 100);"]), nlocs=1)

  ctx.unit("set(): overwrite existing key",
           "\n".join([f"{T.set(ctx.t, k0, '100')};", f"{T.set(ctx.t, k0, '101')};",
                      f"TEST_EQUAL({ctx.call('size', ctx.t)}, 1);",
                      f"TEST_EQUAL({ctx.call('get', ctx.t, k0)}, 101);"]), nlocs=1)

  # Mapping inherits Container.contains over the VALUE type (an LSP wart), so key
  # presence is asserted through the index-typed indexed() alone
  if active(T, "indexed"):
    ctx.unit("indexed(): key presence",
             "\n".join([f"{T.set(ctx.t, k0, '100')};",
                        f"TEST_TRUE({ctx.call('indexed', ctx.t, k0)});",
                        f"TEST_FALSE({ctx.call('indexed', ctx.t, k2)});"]), nlocs=3)

  if active(T, "view"):
    ctx.unit("view(): observe and miss",
             "\n".join([f"{T.set(ctx.t, k0, '101')};",
                        f"TEST_EQUAL(*{ctx.call('view', ctx.t, k0)}, 101);",
                        f"TEST_NULL({ctx.call('view', ctx.t, k2)});"]), nlocs=3)

  if active(T, "remove"):
    ctx.unit("remove(): drop present and reject absent",
             "\n".join([f"{T.set(ctx.t, k0, '100')};", f"{T.set(ctx.t, k1, '101')};",
                        f"TEST_TRUE({ctx.call('remove', ctx.t, k0)});",
                        f"TEST_FALSE({ctx.call('indexed', ctx.t, k0)});",
                        f"TEST_FALSE({ctx.call('remove', ctx.t, k0)});",
                        f"TEST_EQUAL({ctx.call('size', ctx.t)}, 1);"]), nlocs=2)

  if active(T, "emplace"):
    ctx.unit("emplace(): construct in place and reject duplicate",
             "\n".join([f"TEST_TRUE({T.emplace(ctx.t, k0)});",
                        f"TEST_FALSE({T.emplace(ctx.t, k0)});",
                        f"TEST_EQUAL({ctx.call('size', ctx.t)}, 1);"]), nlocs=1)

  if getattr(T, "range", None) is not None:
    r = T.range.variable("r")
    walk = f"for({r} = {T.range.new(ctx.t)}; !{T.range.empty(r)}; {T.range.move_front(r)})"
    body = [f"{T.set(ctx.t, k0, '100')};", f"{T.set(ctx.t, k1, '101')};",
            "size_t n = 0;",
            f"{r.definition}; {walk} {{ ++n; }}",
            f"TEST_EQUAL(n, 2);"]
    ctx.unit("range(): traverse all bindings", "\n".join(body), nlocs=2)


# --------------------------------------------------------------------------- #
# Multiset concept - multiplicity semantics
# --------------------------------------------------------------------------- #

def emit_multiset(ctx):
  x, T, ek = ctx.x, ctx.T, ctx.ek
  a0 = ctx.earg(0)

  if active(T, "put") and active(T, "count"):
    ctx.unit("put()/count(): multiplicity grows",
             "\n".join([f"{ctx.call('put', ctx.t, a0)};", f"{ctx.call('put', ctx.t, a0)};",
                         f"TEST_EQUAL({ctx.call('count', ctx.t, a0)}, 2);"]), nlocs=1)

  if active(T, "emplace") and active(T, "count"):
    ctor_params = getattr(ek.type, "constructor_parameters", None)
    if ctor_params:
      # the ctor args match e0's sample value so count() can observe the insertion
      ctor_args = [str(ek.values[0]) for _ in ctor_params]
      ctx.unit("emplace(): construct in place and count",
               "\n".join([f"TEST_TRUE({ctx.call('emplace', ctx.t, *ctor_args)});",
                          f"TEST_TRUE({ctx.call('emplace', ctx.t, *ctor_args)});",
                          f"TEST_EQUAL({ctx.call('count', ctx.t, ctx.earg(0))}, 2);"]), nlocs=1)
    elif ek.numeric:
      # parameterless kinds construct the zero value the numeric samples start at
      ctx.unit("emplace(): default-construct and count",
               "\n".join([f"TEST_TRUE({ctx.call('emplace', ctx.t)});",
                          f"TEST_EQUAL({ctx.call('count', ctx.t, ctx.earg(0))}, 1);"]))

  if active(T, "remove") and active(T, "count"):
    ctx.unit("remove(): single occurrence",
             "\n".join([f"{ctx.call('put', ctx.t, a0)};", f"{ctx.call('put', ctx.t, a0)};",
                         f"TEST_TRUE({ctx.call('remove', ctx.t, a0)});",
                         f"TEST_EQUAL({ctx.call('count', ctx.t, a0)}, 1);"]), nlocs=1)

  if active(T, "wipe"):
    ctx.unit("wipe(): all occurrences",
             "\n".join([f"{ctx.call('put', ctx.t, a0)};", f"{ctx.call('put', ctx.t, a0)};",
                         f"TEST_EQUAL({ctx.call('wipe', ctx.t, a0)}, 2);",
                         f"TEST_EQUAL({ctx.call('count', ctx.t, a0)}, 0);"]), nlocs=1)

  from autoc.counter import Counter
  if active(T, "equal_range") and getattr(T, "range", None) is not None:
    r = T.range.variable("r")
    ctx.unit("equal_range(): cover all occurrences",
             "\n".join([f"{ctx.call('put', ctx.t, a0)};", f"{ctx.call('put', ctx.t, a0)};",
                         f"{r.definition} = {T.equal_range(ctx.t, a0)};",
                         "size_t n = 0;",
                         f"while(!{T.range.empty(r)}) {{ ++n; {T.range.move_front(r)}; }}",
                         f"TEST_EQUAL(n, {1 if isinstance(T, Counter) else 2});",
                         f"TEST_EQUAL({ctx.call('count', ctx.t, a0)}, 2);"]), nlocs=1)

  if active(T, "add") and active(T, "total_size"):
    ctx.unit("add()/subtract(): bulk multiplicity",
             "\n".join([f"{T.add(ctx.t, a0, '3')};",
                         f"TEST_EQUAL({ctx.call('count', ctx.t, a0)}, 3);",
                         f"TEST_EQUAL({ctx.call('total_size', ctx.t)}, 3);",
                         f"TEST_EQUAL({ctx.call('distinct_size', ctx.t)}, 1);",
                         f"TEST_EQUAL({T.subtract(ctx.t, a0, '1')}, 1);",
                         f"TEST_EQUAL({ctx.call('count', ctx.t, a0)}, 2);"]), nlocs=1)


# --------------------------------------------------------------------------- #
# Multimapping concept - multiple values per key
# --------------------------------------------------------------------------- #

def emit_multimapping(ctx):
  x, T, ek = ctx.x, ctx.T, ctx.ek
  k0 = ctx.earg(0)

  if active(T, "put") and active(T, "count"):
    ctx.unit("put()/count(): multiple values per key",
             "\n".join([f"{T.put(ctx.t, k0, '100')};", f"{T.put(ctx.t, k0, '101')};",
                         f"TEST_EQUAL({ctx.call('count', ctx.t, k0)}, 2);"]), nlocs=1)

  if active(T, "emplace") and active(T, "count"):
    # matrix multimap values are int, so emplace() takes just the key and
    # default-constructs the zero value
    ctx.unit("emplace(): construct value in place",
             "\n".join([f"TEST_TRUE({ctx.call('emplace', ctx.t, k0)});",
                        f"TEST_EQUAL({ctx.call('count', ctx.t, k0)}, 1);"]))

  if active(T, "wipe"):
    ctx.unit("wipe(): all values of a key",
             "\n".join([f"{T.put(ctx.t, k0, '100')};", f"{T.put(ctx.t, k0, '101')};",
                         f"TEST_EQUAL({ctx.call('wipe', ctx.t, k0)}, 2);"]), nlocs=1)


# --------------------------------------------------------------------------- #
# Range concepts - traversal behavior
# --------------------------------------------------------------------------- #

def emit_range(ctx):
  x, T, ek = ctx.x, ctx.T, ctx.ek
  if getattr(T, "range", None) is None or ctx.fill_attr is None:
    return
  r = T.range.variable("r")

  walk = f"for({r} = {T.range.new(ctx.t)}; !{T.range.empty(r)}; {T.range.move_front(r)})"
  body = [ctx.fill(0), ctx.fill(1), ctx.fill(2), "size_t n = 0;",
          f"{r.definition}; {walk} {{ ++n; }}",
          f"TEST_EQUAL(n, {ctx.call('size', ctx.t)});"]
  ctx.unit("range: forward traversal covers the container", "\n".join(body), nlocs=3)

  if isinstance(T.range, DirectAccess) and isinstance(T, Indexable) and not isinstance(T, (SetConcept, Mapping)):
    body = [ctx.fill(0), ctx.fill(1), ctx.fill(2),
            f"{r.definition} = {T.range.new(ctx.t)};",
            ek.assert_call(str(T.range.get(r, "1")), 1, "e1"),
            ek.view_obs(str(T.range.view(r, "1")), 1, "e1"),
            f"TEST_EQUAL({T.range.size(r)}, 3);"]
    ctx.unit("range: direct access matches insertion order", "\n".join(body), nlocs=3)

  if isinstance(T.range, Backward):
    back = f"while(!{T.range.empty(r)}) {{ ++n; {T.range.move_back(r)}; }}"
    body = [ctx.fill(0), ctx.fill(1), ctx.fill(2), "size_t n = 0;",
            f"{r.definition} = {T.range.new(ctx.t)};",
            back,
            "TEST_EQUAL(n, 3);"]
    ctx.unit("range: backward traversal covers the container", "\n".join(body), nlocs=3)


# --------------------------------------------------------------------------- #
# Sortable/Bisectable mixins
# --------------------------------------------------------------------------- #

def emit_sortable(ctx):
  x, T, ek = ctx.x, ctx.T, ctx.ek
  if not ek.orderable or not isinstance(T, Sortable) or ctx.fill_attr is None:
    return

  if active(T, "sort") and active(T, "sorted"):
    body = [ctx.fill(2), ctx.fill(0), ctx.fill(1),
            f"{T.sort(ctx.t)};",
            f"TEST_TRUE({ctx.call('sorted', ctx.t)});"]
    ctx.unit("sort(): order elements", "\n".join(body), nlocs=3)

    if isinstance(T, Indexable) and active(T, "get") and not isinstance(T, SetConcept):
      body = [ctx.fill(2), ctx.fill(0), ctx.fill(1),
              f"{T.sort(ctx.t)};",
              ek.assert_call(ctx.call("get", ctx.t, "0"), 0, "e0"),
              ek.assert_call(ctx.call("get", ctx.t, "2"), 2, "e2")]
      ctx.unit("sort(): ascending arrangement", "\n".join(body), nlocs=3)

  if active(T, "sort") and active(T, "reverse"):
    body = [ctx.fill(0), ctx.fill(1), ctx.fill(2),
            f"{T.sort(ctx.t)};",
            f"{T.reverse(ctx.t)};",
            f"TEST_FALSE({ctx.call('sorted', ctx.t)});"]
    if isinstance(T, Indexable) and active(T, "get"):
      body.append(ek.assert_call(ctx.call("get", ctx.t, "0"), 2, "e2"))
    ctx.unit("reverse(): flip element order", "\n".join(body), nlocs=3)

  if isinstance(T, Bisectable) and active(T, "lower_bound") and active(T, "binary_search"):
    prelude = [ctx.fill(0), ctx.fill(1), ctx.fill(2), f"{T.sort(ctx.t)};"]
    body = prelude + [
      f"TEST_EQUAL({ctx.call('lower_bound', ctx.t, ctx.earg(1))}, 1);",
      f"TEST_EQUAL({ctx.call('upper_bound', ctx.t, ctx.earg(1))}, 2);",
      f"TEST_TRUE({ctx.call('binary_search', ctx.t, ctx.earg(1))});"]
    lit = ek.literal(ek.values[0])
    if lit is not None:
      body.append(f"TEST_FALSE({ctx.call('binary_search', ctx.t, ek.literal('zzz' if ek.name == 'cstring' else 99))});")
    ctx.unit("lower_bound()/upper_bound()/binary_search(): bisection", "\n".join(body), nlocs=3)


# --------------------------------------------------------------------------- #
# Dispatcher invoked by the matrix per (container instance, element kind) cell
# --------------------------------------------------------------------------- #

def emit_all(x, T, ek):
  ctx = Ctx(x, T, ek)
  emit_value(ctx)
  if isinstance(T, Mapping):
    emit_mapping(ctx)
  elif isinstance(T, Multimapping):
    emit_multimapping(ctx)
  else:
    if isinstance(T, Multiset):
      emit_multiset(ctx)
    elif isinstance(T, SetConcept):
      emit_set(ctx)
    else:
      if isinstance(T, Container):
        emit_container(ctx)
      if isinstance(T, Indexable):
        emit_indexed(ctx)
    emit_sequence(ctx)
    emit_sortable(ctx)
  emit_range(ctx)
