import unittest
from metac.core import _Traitful, Composite, Primitive, TraitError, IntersectionType, Comparable, Orderable, Hashable, Copyable, satisfies, require, enforced, Type, Coerce
from metac.ordered import Ordered
from metac.hashed import Hashed
from metac.set import Set
from metac.multiset import Multiset
from metac.mapping import Mapping
from metac.insertable import Insertable
from metac.chained_hash_set import Set as ChainedHashSet
from metac.intrusive_hash_set import Set as IntrusiveHashSet
from metac.btree_set import Set as BTreeSet
from metac.avl_set import Set as AVLSet
from metac.rb_set import Set as RBSet
from metac.treap_set import Set as TreapSet
from metac.flat_set import Set as FlatSet
from metac.flat_multiset import Set as FlatMultiset
from metac.chained_hash_map import Map as ChainedHashMap
from metac.intrusive_hash_map import Map as IntrusiveHashMap
from metac.tree_map import Map as TreeMap
from metac.btree_map import Map as BTreeMap
from metac.flat_map import Map as FlatMap
from metac.flat_multimap import Map as FlatMultimap
from metac.vector import Vector
from metac.list import List
from metac.deque import Deque
from metac.array import Array
from metac.tiered_vector import Vector as TieredVector
from metac.circular_buffer import Static as StaticCircularBuffer, Dynamic as DynamicCircularBuffer
from metac.priority_queue import Queue as PriorityQueue
from metac.counter import Counter
from metac.multimap import Map as Multimap
from metac.queue import Queue
from metac.stack import Stack
from metac.packet import Packet


# Custom non-comparable, non-hashable, non-orderable composite type
class OpaqueType(Composite):

  def __init__(self, name="opaque_t"):
    super().__init__(name)

  def __setup__(self):
    super().__setup__()
    # Define create, copy, destroy so it's a valid copyable type
    with self.create as m:
      m.inline_code = "assert(target); target->value = 0;"
    with self.copy as m:
      m.inline_code = "assert(target); assert(source); target->value = source->value;"
    with self.destroy as m:
      m.inline_code = "assert(target);"

  def _render_struct(self, stream, header):
    super()._render_struct(stream, header)
    stream.append(f"struct {self.name} {{ int value; }};\n")


# Custom type with equality comparison only (no compare, no hash)
class ComparableOnlyType(Composite):

  def __init__(self, name="comp_only_t"):
    super().__init__(name)

  def __setup__(self):
    super().__setup__()
    with self.create as m:
      m.inline_code = "assert(target); target->value = 0;"
    with self.copy as m:
      m.inline_code = "assert(target); assert(source); target->value = source->value;"
    with self.destroy as m:
      m.inline_code = "assert(target);"
    with self.equal as m:
      m.inline_code = "return 1;"

  def _render_struct(self, stream, header):
    super()._render_struct(stream, header)
    stream.append(f"struct {self.name} {{ int value; }};\n")


class MockTraitful(_Traitful):

  def __init__(self, **traits):
    self._traits = traits

  @property
  def comparable(self):
    return self._traits.get("comparable", False)

  @property
  def orderable(self):
    return self._traits.get("orderable", False)

  @property
  def hashable(self):
    return self._traits.get("hashable", False)

  @property
  def copyable(self):
    return self._traits.get("copyable", False)

  @property
  def moveable(self):
    return self._traits.get("moveable", False)

  @property
  def destructible(self):
    return self._traits.get("destructible", False)

  @property
  def default_constructible(self):
    return self._traits.get("default_constructible", False)

  @property
  def zero_initializable(self):
    return self._traits.get("zero_initializable", False)

  @property
  def emplaceable(self):
    return self._traits.get("emplaceable", False)


class TestTraits(unittest.TestCase):

  def test_traitful_enforcers_success(self):
    t = MockTraitful(comparable=True, orderable=True, hashable=True, copyable=True)
    self.assertIs(t.require(Comparable), t)
    self.assertIs(t.require(Orderable), t)
    self.assertIs(t.require(Hashable), t)
    self.assertIs(t.require(Copyable), t)
    self.assertIs(t.require(Comparable & Hashable), t)
    self.assertIs(t.require(Comparable | Orderable), t)
    # Also via TraitProtocol.require(t)
    self.assertIs(Comparable.require(t), t)
    self.assertIs(Orderable.require(t), t)
    self.assertIs(Hashable.require(t), t)
    self.assertIs(Copyable.require(t), t)

  def test_traitful_enforcers_failure(self):
    t = MockTraitful()
    with self.assertRaises(TraitError) as ctx:
      t.require(Comparable)
    self.assertIn("expected Comparable", str(ctx.exception))

    with self.assertRaises(TraitError) as ctx:
      Comparable.require(t)
    self.assertIn("expected Comparable", str(ctx.exception))

    with self.assertRaises(TraitError) as ctx:
      t.require(Orderable)
    self.assertIn("expected Orderable", str(ctx.exception))

    with self.assertRaises(TraitError) as ctx:
      t.require(Hashable)
    self.assertIn("expected Hashable", str(ctx.exception))

    with self.assertRaises(TraitError) as ctx:
      t.require(Copyable)
    self.assertIn("expected Copyable", str(ctx.exception))

    t_partial = MockTraitful(comparable=True, orderable=False)
    with self.assertRaises(TraitError) as ctx:
      t_partial.require(Comparable & Orderable)
    self.assertIn("expected Orderable", str(ctx.exception))

    with self.assertRaises(TraitError) as ctx:
      t.require(Comparable | Hashable)
    self.assertIn("expected", str(ctx.exception))

  def test_ordered_require(self):
    self.assertIs(FlatMap.require(Ordered), FlatMap)
    self.assertIs(TreeMap.require(Ordered), TreeMap)
    self.assertIs(BTreeMap.require(Ordered), BTreeMap)
    self.assertIs(FlatMultimap.require(Ordered), FlatMultimap)
    # Also via Ordered.require
    self.assertIs(Ordered.require(FlatMap), FlatMap)
    self.assertIs(Ordered.require(TreeMap), TreeMap)

    with self.assertRaises(TraitError) as ctx:
      ChainedHashMap.require(Ordered)
    self.assertIn("expected Ordered", str(ctx.exception))

    with self.assertRaises(TraitError) as ctx:
      Ordered.require(ChainedHashMap)
    self.assertIn("expected Ordered", str(ctx.exception))

  def test_hashed_require(self):
    self.assertIs(ChainedHashMap.require(Hashed), ChainedHashMap)
    self.assertIs(IntrusiveHashMap.require(Hashed), IntrusiveHashMap)
    self.assertIs(ChainedHashSet.require(Hashed), ChainedHashSet)
    self.assertIs(IntrusiveHashSet.require(Hashed), IntrusiveHashSet)
    # Also via Hashed.require
    self.assertIs(Hashed.require(ChainedHashMap), ChainedHashMap)
    self.assertIs(Hashed.require(IntrusiveHashMap), IntrusiveHashMap)

    with self.assertRaises(TraitError) as ctx:
      TreeMap.require(Hashed)
    self.assertIn("expected Hashed", str(ctx.exception))

    with self.assertRaises(TraitError) as ctx:
      Hashed.require(TreeMap)
    self.assertIn("expected Hashed", str(ctx.exception))

  def test_type_require(self):
    # Canonical require(target, contract)
    self.assertIs(require(AVLSet, Set), AVLSet)
    self.assertIs(require(Vector, Insertable), Vector)
    self.assertIs(require(FlatMap, Mapping), FlatMap)

    with self.assertRaises(TraitError) as ctx:
      require(Vector, Set)
    self.assertIn("expected Set", str(ctx.exception))

    # Fluent target.require(contract) on container classes
    self.assertIs(AVLSet.require(Set), AVLSet)
    self.assertIs(Vector.require(Insertable), Vector)
    self.assertIs(FlatMap.require(Mapping), FlatMap)
    self.assertIs(AVLSet.require(Set & Ordered), AVLSet)

    with self.assertRaises(TraitError) as ctx:
      Vector.require(Set)
    self.assertIn("expected Set", str(ctx.exception))

    with self.assertRaises(TraitError) as ctx:
      Vector.require(Mapping)
    self.assertIn("expected Mapping", str(ctx.exception))

    with self.assertRaises(TraitError) as ctx:
      AVLSet.require(Mapping)
    self.assertIn("expected Mapping", str(ctx.exception))

    # Fluent target.require(contract) on container instances
    vec_inst = Vector("test_vec_inst", "int")
    self.assertIs(vec_inst.require(Insertable), vec_inst)

    set_inst = AVLSet("test_set_inst", "int")
    self.assertIs(set_inst.require(Set), set_inst)
    self.assertIs(set_inst.require(Ordered), set_inst)

    map_inst = FlatMap("test_map_inst", "int", "int")
    self.assertIs(map_inst.require(Mapping), map_inst)
    self.assertIs(map_inst.require(Ordered), map_inst)

  def test_negative_container_instantiations(self):
    opaque = OpaqueType("neg_opaque_t")
    # Priority queue demands orderable
    with self.assertRaises(TraitError) as ctx:
      PriorityQueue("neg_pq", opaque)
    self.assertIn("orderable", str(ctx.exception).lower())

    # Set demands comparable
    with self.assertRaises(TraitError) as ctx:
      Set("neg_set", opaque)
    self.assertIn("comparable", str(ctx.exception).lower())

    # Multiset demands comparable
    with self.assertRaises(TraitError) as ctx:
      Multiset("neg_multiset", opaque)
    self.assertIn("comparable", str(ctx.exception).lower())

    comp_only = ComparableOnlyType("neg_comp_only_t")
    # Hash sets demand hashable
    with self.assertRaises(TraitError) as ctx:
      ChainedHashSet("neg_chs", comp_only)
    self.assertIn("hashable", str(ctx.exception).lower())

    # Tree and flat sets demand orderable
    with self.assertRaises(TraitError) as ctx:
      AVLSet("neg_avl", comp_only)
    self.assertIn("orderable", str(ctx.exception).lower())

    with self.assertRaises(TraitError) as ctx:
      FlatSet("neg_flat_set", comp_only)
    self.assertIn("orderable", str(ctx.exception).lower())

    with self.assertRaises(TraitError) as ctx:
      FlatMultiset("neg_flat_multiset", comp_only)
    self.assertIn("orderable", str(ctx.exception).lower())

    # Maps demand index traits
    with self.assertRaises(TraitError) as ctx:
      ChainedHashMap("neg_chm", "int", comp_only)
    self.assertIn("hashable", str(ctx.exception).lower())

    with self.assertRaises(TraitError) as ctx:
      TreeMap("neg_tm_key", "int", comp_only, AVLSet)
    self.assertIn("orderable", str(ctx.exception).lower())

    with self.assertRaises(TraitError) as ctx:
      TreeMap("neg_tm_backend", "int", "int", ChainedHashSet)
    self.assertIn("expected Ordered", str(ctx.exception))

    # Tree map rejects an ordered collection that is NOT a Set (e.g. FlatMap)
    with self.assertRaises(TraitError) as ctx:
      TreeMap("neg_tm_not_set", "int", "int", FlatMap)
    self.assertIn("expected Set", str(ctx.exception))

    with self.assertRaises(TraitError) as ctx:
      FlatMap("neg_fm", "int", comp_only)
    self.assertIn("orderable", str(ctx.exception).lower())

    with self.assertRaises(TraitError) as ctx:
      FlatMultimap("neg_fmm", "int", comp_only)
    self.assertIn("orderable", str(ctx.exception).lower())

    # Counter demands mapping backend
    with self.assertRaises(TraitError) as ctx:
      Counter("neg_cnt", "int", Vector)
    self.assertIn("expected Mapping", str(ctx.exception))

    # Multimap demands set and insertable+traversable collection backends
    with self.assertRaises(TraitError) as ctx:
      Multimap("neg_mm_set", "int", "int", set=Vector, collection=Vector)
    self.assertIn("expected Set", str(ctx.exception))

    with self.assertRaises(TraitError) as ctx:
      Multimap("neg_mm_col", "int", "int", set=AVLSet, collection=ChainedHashMap)
    self.assertIn("expected Insertable", str(ctx.exception))

    # Multimap rejects an Insertable collection that is NOT Traversable (e.g. PriorityQueue)
    with self.assertRaises(TraitError) as ctx:
      Multimap("neg_mm_pq", "int", "int", set=AVLSet, collection=PriorityQueue)
    self.assertIn("expected Traversable", str(ctx.exception))

  def test_map_payload_freedom(self):
    opaque = OpaqueType("payload_opaque_t")
    # All maps should successfully instantiate with unhashable, non-comparable values
    chm = ChainedHashMap("test_chm_opaque", opaque, "int")
    tm = TreeMap("test_tm_opaque", opaque, "int", AVLSet)
    bm = BTreeMap("test_bm_opaque", opaque, "int")
    fm = FlatMap("test_fm_opaque", opaque, "int")
    fmm = FlatMultimap("test_fmm_opaque", opaque, "int")

    for m in (chm, tm, bm, fm, fmm):
      stream = []
      m.render_declarations(stream, True)
      m.render_definitions(stream, False)
      rendered = "".join(stream)
      self.assertTrue(len(rendered) > 0)

  def test_sequences_with_opaque_elements(self):
    opaque = OpaqueType("seq_opaque_t")
    vec = Vector("test_vec_opaque", opaque)
    lst = List("test_list_opaque", opaque)
    deq = Deque("test_deq_opaque", opaque)
    arr = Array("test_arr_opaque", opaque, 5)
    tv = TieredVector("test_tv_opaque", opaque)
    cb = DynamicCircularBuffer("test_cb_opaque", opaque)
    fcb = StaticCircularBuffer("test_fcb_opaque", opaque, 8)

    self.assertFalse(vec.comparable)
    self.assertFalse(vec.hashable)
    self.assertFalse(vec.equal.active)
    self.assertFalse(vec.hash.active)

    self.assertFalse(arr.comparable)
    self.assertFalse(arr.hashable)
    self.assertFalse(arr.equal.active)
    self.assertFalse(arr.hash.active)

    for c in (vec, lst, deq, arr, tv, cb, fcb):
      stream = []
      c.render_declarations(stream, True)
      c.render_definitions(stream, False)
      rendered = "".join(stream)
      self.assertTrue(len(rendered) > 0)

  def test_type_algebra(self):
    # IntersectionType creation and composition
    contract = Set & Ordered
    self.assertIsInstance(contract, IntersectionType)
    self.assertEqual(contract.__args__, (Set, Ordered))

    # Chaining intersections
    chained = Set & Ordered & Insertable
    self.assertEqual(chained.__args__, (Set, Ordered, Insertable))

    # Union with intersection
    union_contract = (Set & Ordered) | Mapping
    self.assertTrue(satisfies(AVLSet, union_contract))
    self.assertTrue(satisfies(FlatMap, union_contract))
    self.assertFalse(satisfies(Vector, union_contract))

    # Trait protocols
    self.assertTrue(satisfies("int", Comparable | Orderable))
    self.assertTrue(satisfies("int", Comparable & Orderable))
    self.assertTrue(satisfies("int", Hashable))

    co = ComparableOnlyType()
    self.assertTrue(satisfies(co, Comparable))
    self.assertFalse(satisfies(co, Orderable))
    self.assertTrue(satisfies(co, Comparable | Orderable))
    self.assertFalse(satisfies(co, Comparable & Orderable))

    op = OpaqueType()
    self.assertFalse(satisfies(op, Comparable))
    self.assertFalse(satisfies(op, Orderable))
    self.assertFalse(satisfies(op, Hashable))

    # Container satisfying IntersectionType
    self.assertTrue(satisfies(AVLSet, Set & Ordered))
    self.assertFalse(satisfies(ChainedHashSet, Set & Ordered))
    self.assertTrue(satisfies(ChainedHashSet, Set & Hashed))
    self.assertFalse(satisfies(FlatMap, Set & Ordered))
    self.assertTrue(satisfies(FlatMap, Mapping & Ordered))

  def test_fluent_require(self):
    # Target-oriented require on classes
    self.assertIs(AVLSet.require(Set & Ordered), AVLSet)
    self.assertIs(FlatMap.require(Mapping & Ordered), FlatMap)
    self.assertIs(ChainedHashMap.require(Mapping & Hashed), ChainedHashMap)

    with self.assertRaises(TraitError) as ctx:
      ChainedHashMap.require(Ordered)
    self.assertIn("expected Ordered", str(ctx.exception))

    with self.assertRaises(TraitError) as ctx:
      Vector.require(Set & Ordered)
    self.assertIn("expected Set", str(ctx.exception))

    # Target-oriented require on instances
    vec = Vector("fluent_vec", "int")
    self.assertIs(vec.require(Insertable), vec)
    self.assertIs(vec.element.require(Comparable), vec.element)
    self.assertIs(vec.element.require(Orderable), vec.element)

  def test_paradigm_b_factories(self):
    # FlatMap Paradigm B factory
    fm = FlatMap("fm_b", "int", "int")
    s_default = fm._make_set()
    self.assertIsInstance(s_default, FlatSet)
    s_avl = fm._make_set(backend=AVLSet)
    self.assertIsInstance(s_avl, AVLSet)

    with self.assertRaises(TraitError) as ctx:
      fm._make_set(backend=ChainedHashSet)
    self.assertIn("expected Ordered", str(ctx.exception))

    with self.assertRaises(TraitError) as ctx:
      fm._make_set(backend=Vector)
    self.assertIn("expected Set", str(ctx.exception))

    # Queue Paradigm B factory
    q = Queue("q_b", "int")
    d_default = q._make_deque()
    self.assertIsInstance(d_default, Deque)

    with self.assertRaises(TraitError) as ctx:
      q._make_deque(backend=AVLSet)
    self.assertIn("expected Sequential", str(ctx.exception))

    # Stack Paradigm B factory
    stk = Stack("stk_b", "int")
    l_default = stk._make_list()
    self.assertIsInstance(l_default, List)

    with self.assertRaises(TraitError) as ctx:
      stk._make_list(backend=AVLSet)
    self.assertIn("expected Sequential", str(ctx.exception))

  def test_coercion_type(self):
    c1 = Coerce[Comparable | Orderable]
    self.assertEqual(repr(c1), "(str | Type) -> (Comparable | Orderable)")

    c2 = Coerce[str | Type, Comparable | Orderable]
    self.assertEqual(repr(c2), "(str | Type) -> (Comparable | Orderable)")

    c3 = Coerce[str | Type] >> (Comparable | Orderable)
    self.assertEqual(repr(c3), "(str | Type) -> (Comparable | Orderable)")

    c4 = Type[Comparable | Orderable]
    self.assertEqual(repr(c4), "(str | Type) -> (Comparable | Orderable)")

    # Coercion satisfaction checks
    self.assertTrue(satisfies("int", c1))
    self.assertTrue(satisfies(Primitive("int"), c1))
    self.assertFalse(satisfies(123, c1))
    self.assertFalse(satisfies(OpaqueType(), c1))

    # Argument coercion via @enforced
    @enforced
    def dummy_func(param: Coerce[Comparable | Orderable]):
      return param

    res = dummy_func("int")
    self.assertIsInstance(res, Type)
    self.assertEqual(res.name, "int")

    # Rejection of un-coercible or trait-failing values with formatted diagnostics
    with self.assertRaises(TraitError) as ctx:
      dummy_func(OpaqueType("bad_opaque"))
    self.assertIn("expected (str | Type) -> (Comparable | Orderable), got OpaqueType", str(ctx.exception))

    with self.assertRaises(TraitError) as ctx:
      dummy_func(999)
    self.assertIn("expected (str | Type) -> (Comparable | Orderable), got int", str(ctx.exception))

    # Coercion in Union contracts
    @enforced
    def dummy_union_func(param: Coerce[Comparable] | None = None):
      return param

    res_union = dummy_union_func("int")
    self.assertIsInstance(res_union, Type)
    self.assertEqual(res_union.name, "int")
    self.assertIsNone(dummy_union_func(None))

    # Compound and Coercion require methods
    self.assertIs((Set & Ordered).require(AVLSet), AVLSet)
    with self.assertRaises(TraitError) as ctx:
      (Set & Ordered).require(Vector)
    self.assertIn("expected Set", str(ctx.exception))

    self.assertEqual(Coerce[Comparable].require("int"), "int")
    with self.assertRaises(TraitError) as ctx:
      Coerce[Comparable].require(OpaqueType())
    self.assertIn("expected (str | Type) -> (Comparable), got OpaqueType", str(ctx.exception))

    # Container-level element validation via Container.__init__
    with self.assertRaises(TraitError) as ctx:
      Vector("bad_vec", 12345)
    self.assertIn("expected (str | Type) -> (Type), got int", str(ctx.exception))

    # Multimap and Counter coerce string types correctly
    mm = Multimap("test_mm_str", "int", "int")
    self.assertIsInstance(mm.element, Type)
    self.assertIsInstance(mm.index, Type)

    cnt = Counter("test_cnt_str", "int")
    self.assertIsInstance(cnt.element, Type)

    # Component decoration: internal subcomponents are hidden/private by default
    vec = Vector("my_vec", "int")
    self.assertEqual(vec._decorate_component("node"), "_my_vecn")
    self.assertEqual(vec._decorate_component("variant", abbreviate=False, hidden=True), "_my_vec_variant")
    self.assertEqual(vec._decorate_component("range", abbreviate=False, hidden=False), "my_vec_range")
    self.assertEqual(vec._decorate_component("range", abbreviate=True, hidden=False), "my_vecr")

    # Packet range is public
    pkt = Packet("test_pkt", "int", 3)
    self.assertEqual(pkt.range.name, "test_pkt_range")


# Run tests when imported or executed directly
suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestTraits)
runner = unittest.TextTestRunner()
result = runner.run(suite)
assert result.wasSuccessful(), f"Trait tests failed: {result.errors} {result.failures}"

if __name__ == "__main__":
  unittest.main()
