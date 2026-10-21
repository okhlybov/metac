# The catalog of the MetaC containers as they are presented in the reference manual.
#
# The base library renders the markup with the exact generated identifiers so the
# documentation of a concrete module references the concrete expanded code. This
# catalog instantiates each container once with the generic value types and overrides
# the display name only, which turns the same declarations into a C++-flavoured
# reference: List<T>, Map<K, T>, List<T>::Range and so on while every operation keeps
# its generated C identifier so an entry in the manual matches the generated code.

import metac.core
import metac.std as std
import metac.list
import metac.deque
import metac.vector
import metac.tiered_vector
import metac.stack
import metac.queue
import metac.priority_queue
import metac.string
import metac.string_buffer
import metac.chained_hash_set
import metac.chained_hash_map
import metac.flat_set
import metac.flat_multiset
import metac.flat_map
import metac.flat_multimap
import metac.multimap
import metac.intrusive_hash_set
import metac.intrusive_hash_map
import metac.treap_set
import metac.rb_set
import metac.avl_set
import metac.btree_set
import metac.tree_map
import metac.btree_map
import metac.record
import metac.variant
import metac.reference
import metac.packet
import metac.array
import metac.bit_array
import metac.bit_vector
import metac.circular_buffer
import metac.counter


# The manual is written with the default CamelCase identifiers
metac.core.decorator = metac.core.camel_decorator


class Placeholder(metac.core._AliasRenderer, metac.core.Primitive):

  def render_declarations(self, stream, header):
    super().render_declarations(stream, header)
    if header:
      stream.append(f"""
        /**
         * @ingroup {self.name}
         * @brief {self.brief if self.brief else self.name}
         */
        typedef struct {self.name} {self.name};
      """)


# Generic value types standing for the concrete element, key and mapped types
T = Placeholder(
  "T",
  brief="Generic element type placeholder",
  description="""
    Stands for the element type of a sequence, set, stack, queue or priority queue —
    and the mapped value type of a map.
  """,
)
K = Placeholder(
  "K",
  brief="Generic index type placeholder",
  description="""
    Stands for the index (key) type of a map.
  """,
)


# The sentinel operations the intrusive containers need are left symbolic - the manual
# declares the generic API and is never compiled, so the sentinels stay abstract
_sentinels = {
  "empty": (lambda element: f"{element} == T_EMPTY", lambda element: f"{element} = T_EMPTY"),
  "deleted": (lambda element: f"{element} == T_DELETED", lambda element: f"{element} = T_DELETED"),
}


def _nested_range(module, name):
  # The range class is selected by the container's own module at construction time,
  # so specializing the module attribute is enough to present the range as the
  # nested List<T>::Range style type of its container
  base = module.Range

  class Range(base):
    @property
    def _doxygen_type(self):
      return f"{self.iterable._doxygen_type}::Range"

  Range.__name__ = name
  Range.__qualname__ = name
  module.Range = Range
  return Range


# Generic element sequences
class List(metac.list.List):
  @property
  def _doxygen_type(self):
    return f"{self.name}<{self.element}>"


class Deque(metac.deque.Deque):
  @property
  def _doxygen_type(self):
    return f"{self.name}<{self.element}>"


# The index type of the direct access containers is an implementation detail
class Vector(metac.vector.Vector):
  @property
  def _doxygen_type(self):
    if self.inline_capacity > 0:
      return f"{self.name}<{self.element}, {self.inline_capacity}>"
    return f"{self.name}<{self.element}>"


class Array(metac.array.Array):
  @property
  def _doxygen_type(self):
    return f"{self.name}<{self.element}, N>"


class Packet(metac.packet.Packet):
  @property
  def _doxygen_type(self):
    return f"{self.name}<{self.element}, N>"


class TieredVector(metac.tiered_vector.Vector):
  @property
  def _doxygen_type(self):
    return f"{self.name}<{self.element}>"


# Adapters
class Stack(metac.stack.Stack):
  @property
  def _doxygen_type(self):
    return f"{self.name}<{self.element}>"


class Queue(metac.queue.Queue):
  @property
  def _doxygen_type(self):
    return f"{self.name}<{self.element}>"


class PriorityQueue(metac.priority_queue.Queue):
  @property
  def _doxygen_type(self):
    return f"{self.name}<{self.element}>"


class String(metac.string.String):
  @property
  def _doxygen_type(self):
    return f"{self.name}<{self.element}>"


class StringBuffer(metac.string_buffer.Buffer):
  @property
  def _doxygen_type(self):
    return f"{self.name}<{self.element}>"


class BitArray(metac.bit_array.Array):
  @property
  def _doxygen_type(self):
    return f"{self.name}<N>"


class BitVector(metac.bit_vector.Vector):
  pass


# Sets
class ChainedHashSet(metac.chained_hash_set.Set):
  @property
  def _doxygen_type(self):
    return f"{self.name}<{self.element}>"


class IntrusiveHashSet(metac.intrusive_hash_set.Set):
  @property
  def _doxygen_type(self):
    return f"{self.name}<{self.element}>"


class TreapSet(metac.treap_set.Set):
  @property
  def _doxygen_type(self):
    return f"{self.name}<{self.element}>"


class RBSet(metac.rb_set.Set):
  @property
  def _doxygen_type(self):
    return f"{self.name}<{self.element}>"


class AVLSet(metac.avl_set.Set):
  @property
  def _doxygen_type(self):
    return f"{self.name}<{self.element}>"


class BTreeSet(metac.btree_set.Set):
  @property
  def _doxygen_type(self):
    return f"{self.name}<{self.element}>"


class FlatSet(metac.flat_set.Set):
  @property
  def _doxygen_type(self):
    return f"{self.name}<{self.element}>"


class FlatMultiset(metac.flat_multiset.Set):
  @property
  def _doxygen_type(self):
    return f"{self.name}<{self.element}>"


# Maps - the index (key) comes first in the C++-flavoured presentation
class ChainedHashMap(metac.chained_hash_map.Map):
  @property
  def _doxygen_type(self):
    return f"{self.name}<{self.index}, {self.element}>"


class IntrusiveHashMap(metac.intrusive_hash_map.Map):
  @property
  def _doxygen_type(self):
    return f"{self.name}<{self.index}, {self.element}>"


class TreeMap(metac.tree_map.Map):
  @property
  def _doxygen_type(self):
    return f"{self.name}<{self.index}, {self.element}>"


class BTreeMap(metac.btree_map.Map):
  @property
  def _doxygen_type(self):
    return f"{self.name}<{self.index}, {self.element}>"


class FlatMap(metac.flat_map.Map):
  @property
  def _doxygen_type(self):
    return f"{self.name}<{self.index}, {self.element}>"


# Multimaps
class FlatMultimap(metac.flat_multimap.Map):
  @property
  def _doxygen_type(self):
    return f"{self.name}<{self.index}, {self.element}>"


class Multimap(metac.multimap.Map):
  @property
  def _doxygen_type(self):
    return f"{self.name}<{self.index}, {self.element}>"


# Multisets
class Counter(metac.counter.Counter):
  @property
  def _doxygen_type(self):
    return f"{self.name}<{self.element}>"



# References
class Counted(metac.reference.Counted):
  @property
  def _doxygen_type(self):
    return f"{self.name}<{self.type}>"


class Raw(metac.reference.Raw):
  @property
  def _doxygen_type(self):
    return f"{self.name}<{self.type}>"


class StaticCircularBuffer(metac.circular_buffer.Static):
  @property
  def _doxygen_type(self):
    return f"{self.name}<{self.element}>"


class DynamicCircularBuffer(metac.circular_buffer.Dynamic):
  @property
  def _doxygen_type(self):
    return f"{self.name}<{self.element}>"


# Specialize the ranges of every container before any of them is instantiated
_nested_range(metac.list, "ListRange")
_nested_range(metac.deque, "DequeRange")
_nested_range(metac.vector, "VectorRange")
_nested_range(metac.array, "ArrayRange")
_nested_range(metac.packet, "PacketRange")
_nested_range(metac.tiered_vector, "TieredVectorRange")
_nested_range(metac.stack, "StackRange")
_nested_range(metac.queue, "QueueRange")
_nested_range(metac.string, "StringRange")
_nested_range(metac.chained_hash_set, "ChainedHashSetRange")
_nested_range(metac.intrusive_hash_set, "IntrusiveHashSetRange")
_nested_range(metac.treap_set, "TreapSetRange")
_nested_range(metac.rb_set, "RBSetRange")
_nested_range(metac.avl_set, "AVLSetRange")
_nested_range(metac.btree_set, "BTreeSetRange")
_nested_range(metac.flat_set, "FlatSetRange")
_nested_range(metac.flat_multiset, "FlatMultisetRange")
_nested_range(metac.flat_multimap, "FlatMultimapRange")
_nested_range(metac.multimap, "MultimapRange")
_nested_range(metac.circular_buffer, "CircularBufferRange")
_nested_range(metac.counter, "CounterRange")


def configure_module(module):
  module.add(T)
  module.add(K)

  module.add(Array("Array", T, 4))
  module.add(AVLSet("AVLSet", T))
  module.add(BitArray("BitArray", 64))
  module.add(BitVector("BitVector"))
  module.add(BTreeMap("BTreeMap", T, K))
  module.add(BTreeSet("BTreeSet", T))
  module.add(ChainedHashMap("ChainedHashMap", T, K))
  module.add(ChainedHashSet("ChainedHashSet", T))
  module.add(Counted(T, name="Counted"))
  module.add(Counter("Counter", T, FlatMap))
  module.add(Deque("Deque", T))
  module.add(DynamicCircularBuffer("DynamicCircularBuffer", T))
  module.add(FlatMap("FlatMap", T, K))
  module.add(FlatMultimap("FlatMultimap", T, K))
  module.add(Multimap("Multimap", T, K, AVLSet, Vector))
  module.add(FlatMultiset("FlatMultiset", T))
  module.add(FlatSet("FlatSet", T))
  module.add(IntrusiveHashMap("IntrusiveHashMap", T, K, _sentinels))
  module.add(IntrusiveHashSet("IntrusiveHashSet", T, _sentinels))
  module.add(List("List", T))
  module.add(PriorityQueue("PriorityQueue", T))
  module.add(Queue("Queue", T))
  module.add(Raw(T, name="Raw"))
  module.add(RBSet("RBSet", T))
  module.add(metac.record.Record("Record", {"first": T, "second": K}))
  module.add(Stack("Stack", T))
  module.add(StaticCircularBuffer("StaticCircularBuffer", T, 4))
  module.add(Packet("Packet", T, 4))
  module.add(String("String"))
  module.add(StringBuffer("StringBuffer"))
  module.add(TieredVector("TieredVector", T))
  module.add(TreeMap("TreeMap", T, K, RBSet))
  module.add(TreapSet("TreapSet", T))
  module.add(metac.variant.Variant("Variant", {"first": T, "second": K}))
  module.add(Vector("Vector", T))

  # Ensure documentation topics are sorted with generic element types (T, K) on top
  sorted_groups = sorted(
    [e for e in module.entities if getattr(e, "public", False) and hasattr(e, "_doxygen_type")],
    key=lambda e: (0 if e.name == "T" else (1 if e.name == "K" else 2), e._doxygen_type),
  )
  group_decls = "\n".join(f"/** @defgroup {e.name} {e._doxygen_type} */" for e in sorted_groups)
  module.add(metac.core.Code(interface=f"\n{group_decls}\n"))

  return module
