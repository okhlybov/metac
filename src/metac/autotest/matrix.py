# The curated container x element-kind registry driving the programmatic suite.
#
# Each row pairs a container factory (a callable name + element kind -> type
# instance, encapsulating family-specific kwargs like capacities, sentinel
# emitters and backends) with the element kinds it is instantiated over. The
# applicability rules live here (orderable-only families exclude the record
# kind, intrusive families need per-kind sentinel emitters); the per-method
# adaptation happens in concepts.py via trait probing.


import metac.std as std
from metac.vector import Vector
from metac.packet import Packet
from metac.array import Array
from metac.tiered_vector import Vector as TieredVector
from metac.list import List
from metac.deque import Deque
from metac.circular_buffer import Static as StaticCircularBuffer
from metac.circular_buffer import Dynamic as DynamicCircularBuffer
from metac.stack import Stack
from metac.queue import Queue
from metac.priority_queue import Queue as PriorityQueue
from metac.chained_hash_set import Set as ChainedHashSet
from metac.intrusive_hash_set import Set as IntrusiveHashSet
from metac.rb_set import Set as RbSet
from metac.avl_set import Set as AvlSet
from metac.treap_set import Set as TreapSet
from metac.flat_set import Set as FlatSet
from metac.btree_set import Set as BTreeSet
from metac.chained_hash_map import Map as ChainedHashMap
from metac.flat_map import Map as FlatMap
from metac.tree_map import Map as TreeMap
from metac.btree_map import Map as BTreeMap
from metac.intrusive_hash_map import Map as IntrusiveHashMap
from metac.flat_multimap import Map as FlatMultimap
from metac.flat_multiset import Set as FlatMultiset
from metac.multimap import Map as Multimap
from metac.counter import Counter

from metac.autotest import Type
from metac.autotest import concepts
from metac.autotest.elements import KINDS


ALL = ("int", "cstring", "comp", "arc", "rec")
ORDERED = ("int", "cstring", "comp")


# Intrusive open addressing encodes slot states as sentinel element values -
# the emitters are chosen per element kind (INT_MIN/INT_MAX for ints, low
# pointer values for counted references)
def _int_sentinels():
  return {
    "empty": (lambda e: f"{e} == INT_MIN", lambda e: f"{e} = INT_MIN"),
    "deleted": (lambda e: f"{e} == INT_MAX", lambda e: f"{e} = INT_MAX"),
  }


def _arc_sentinels():
  return {
    "empty": (lambda e: f"{e} == (int*)(size_t)2", lambda e: f"{e} = (int*)(size_t)2"),
    "deleted": (lambda e: f"{e} == (int*)(size_t)1", lambda e: f"{e} = (int*)(size_t)1"),
  }


# Map sentinels receive the whole entry expression and mark its index field -
# keeping the mark on one field spares memory debuggers from untouching the rest
def _int_entry_sentinels():
  return {
    "empty": (lambda e: f"{e}.index == INT_MIN", lambda e: f"{e}.index = INT_MIN"),
    "deleted": (lambda e: f"{e}.index == INT_MAX", lambda e: f"{e}.index = INT_MAX"),
  }


# Simple rows: (factory, family name, kinds) where factory takes (name, element)
def _simple(cls, **kwargs):
  return lambda name, element: cls(name, element, **kwargs)

ROWS = (
  (_simple(Vector), "vector", ALL),
  (lambda name, element: Vector(name, element, inline_capacity=4), "inlined_vector", ("int", "comp")),  # the inline<->heap storage transitions the plain vector rows never take
  (_simple(Packet, capacity=8), "packet", ("int", "cstring")),  # slots default-construct: parametrized-create kinds excluded
  (_simple(Array, size=8), "array", ("int", "cstring")),
  (_simple(TieredVector), "tiered", ("int", "cstring", "rec")),  # growth default-constructs slots: parametrized-create kinds excluded
  (_simple(List), "list", ALL),
  (_simple(Deque), "deque", ALL),
  (_simple(StaticCircularBuffer, capacity=4), "scbuffer", ("int", "cstring")),
  (_simple(DynamicCircularBuffer), "dbuffer", ("int", "comp", "arc", "rec")),
  (_simple(Stack), "stack", ("int", "cstring", "comp", "arc", "rec")),
  (_simple(Queue), "queue", ("int", "cstring", "comp", "arc", "rec")),
  (_simple(PriorityQueue), "pqueue", ("int", "cstring")),
  (_simple(ChainedHashSet), "chained_set", ALL),
  (lambda name, element: IntrusiveHashSet(name, element, _int_sentinels(), dependencies=(std.limits_h,)),
   "intrusive_set", ("int",)),
  (lambda name, element: IntrusiveHashSet(name, element, _arc_sentinels()),
   "intrusive_set", ("arc",)),
  (_simple(RbSet), "rb_set", ORDERED),
  (_simple(AvlSet), "avl_set", ORDERED),
  (_simple(TreapSet), "treap_set", ORDERED),
  (_simple(FlatSet), "flat_set", ORDERED),
  (_simple(FlatMultiset), "flat_multiset", ORDERED),
  (_simple(BTreeSet, order=4), "btree_set", ORDERED),
  (_simple(BTreeSet, order=3), "btree3_set", ORDERED),
  (_simple(BTreeSet, order=8), "btree8_set", ORDERED),
)


# Keyed rows: factory takes (name, value type, key element); map values are int
def _map_simple(cls, **kwargs):
  return lambda name, value, key: cls(name, value, key, **kwargs)

MAP_ROWS = (
  (_map_simple(ChainedHashMap), "chained_hash_map", ("int", "cstring", "comp")),
  (_map_simple(FlatMap), "flat_map", ("int", "cstring")),
  (_map_simple(TreeMap, set=RbSet), "rb_tree_map", ("int", "cstring")),
  (_map_simple(TreeMap, set=AvlSet), "avl_tree_map", ("int", "cstring")),
  (_map_simple(TreeMap, set=TreapSet), "treap_tree_map", ("int", "cstring")),
  (_map_simple(BTreeMap, order=4), "btree_map", ORDERED),
  (_map_simple(BTreeMap, order=3), "btree3_map", ORDERED),
  (_map_simple(BTreeMap, order=8), "btree8_map", ORDERED),
  (lambda name, value, key: IntrusiveHashMap(name, value, key, _int_entry_sentinels(), dependencies=(std.limits_h,)),
   "intrusive_hash_map", ("int",)),
  (_map_simple(FlatMultimap), "flat_multimap", ("int",)),
  (lambda name, value, key: Multimap(name, value, key, AvlSet, Vector), "multimap", ("int",)),
  (lambda name, value, key: Multimap(name, value, key, RbSet, Vector), "rb_multimap", ("int",)),
  (lambda name, value, key: Multimap(name, value, key, TreapSet, Vector), "treap_multimap", ("int",)),
  (lambda name, value, key: Multimap(name, value, key, ChainedHashSet, Vector), "chained_multimap", ("int",)),
  (lambda name, value, key: Multimap(name, value, key, AvlSet, List), "list_multimap", ("int",)),
)

COUNTER_ROWS = (
  (lambda name, element: Counter(name, element, backend=FlatMap), "counter_flat", ("int", "cstring", "comp")),
  (lambda name, element: Counter(name, element, backend=ChainedHashMap), "counter_chained", ALL),
)


def build():
  # Plain and set containers: one instantiation per (family, element kind) cell
  for factory, family, kinds in ROWS:
    for kind in kinds:
      ek = KINDS[kind]
      T = factory(f"{kind}_{family}", ek.type)
      concepts.emit_all(Type(T), T, ek)

  # Keyed containers: the element kind describes the key, values are int
  for factory, family, kinds in MAP_ROWS:
    for kind in kinds:
      ek = KINDS[kind]
      T = factory(f"{kind}2int_{family}", "int", ek.type)
      concepts.emit_all(Type(T), T, ek)

  for factory, family, kinds in COUNTER_ROWS:
    for kind in kinds:
      ek = KINDS[kind]
      T = factory(f"{kind}_{family}", ek.type)
      concepts.emit_all(Type(T), T, ek)


build()
