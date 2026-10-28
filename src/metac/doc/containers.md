# Container catalog {#containers}

Every container below is documented in this manual as a single generic type, instantiated
with the placeholders `T` and `K` (see @ref index). The *Python module* is what you
import in your module script; the *type* is the class you instantiate with a concrete C type.

## Sequences

| Module | Type | Documented as | Range | Notes |
|---|---|---|---|---|
| `metac.list` | `List` | `List<T>` | `List<T>::Range` (forward) | singly linked; `O(1)` push/pop at the front |
| `metac.deque` | `Deque` | `Deque<T>` | `Deque<T>::Range` (bidirectional) | doubly linked; both ends are `O(1)` |
| `metac.vector` | `Vector` | `Vector<T>` | `Vector<T>::Range` (direct access) | contiguous dynamic storage, amortized `O(1)` push/pop, indexed access, sorting and binary search; optional inline capacity for small buffer optimization |
| `metac.array` | `Array` | `Array<T, N>` | `Array<T, N>::Range` (direct access) | fixed size, stack-allocated contiguous C array, zero heap allocation |
| `metac.packet` | `Packet` | `Packet<T, N>` | `Packet<T, N>::Range` (direct access) | fixed capacity, stack-allocated, zero heap allocation; vector-like packet backed by a bounded C array |
| `metac.circular_buffer` | `Static`, `Dynamic` | `StaticCircularBuffer<T>`, `DynamicCircularBuffer<T>` | `StaticCircularBuffer<T>::Range`, `DynamicCircularBuffer<T>::Range` (direct access) | stack or heap-allocated circular ring buffer |
| `metac.tiered_vector` | `Vector` | `TieredVector<T>` | `TieredVector<T>::Range` (direct access) | chunked; amortized `O(1)` append with stable addresses |
| `metac.stack` | `Stack` | `Stack<T>` | `Stack<T>::Range` (forward) | LIFO adapter over the list |
| `metac.queue` | `Queue` | `Queue<T>` | `Queue<T>::Range` (forward) | FIFO adapter over the deque |
| `metac.priority_queue` | `Queue` | `PriorityQueue<T>` | — | binary heap; `pop` yields the greatest element, duplicates allowed |
| `metac.string` | `String` | `String<char>` | `String<char>::Range` (direct access) | string as an index→character map; variadic formatted output (`format`) |
| `metac.string_buffer` | `Buffer` | `StringBuffer<char>` | — | append-optimized string buffer with scratch accumulation and lazy joining |

## Sets

| Module | Type | Documented as | Range | Notes |
|---|---|---|---|---|
| `metac.chained_hash_set` | `Set` | `ChainedHashSet<T>` | `ChainedHashSet<T>::Range` (forward) | bucket chaining; no sentinels, stable element addresses, safe default |
| `metac.intrusive_hash_set` | `Set` | `IntrusiveHashSet<T>` | `IntrusiveHashSet<T>::Range` (forward) | flat open addressing; needs sentinel values for the element type |
| `metac.treap_set` | `Set` | `TreapSet<T>` | `TreapSet<T>::Range` (bidirectional) | ordered; iterates sorted, randomized BST with algebraic set operations |
| `metac.rb_set` | `Set` | `RBSet<T>` | `RBSet<T>::Range` (bidirectional) | ordered; red-black tree with guaranteed O(log n) height and <= 3 rotations on removal |
| `metac.avl_set` | `Set` | `AVLSet<T>` | `AVLSet<T>::Range` (bidirectional) | ordered; strictly balanced AVL tree with height <= 1.44 log2(n), fastest lookups |
| `metac.btree_set` | `Set` | `BTreeSet<T>` | `BTreeSet<T>::Range` (bidirectional) | ordered; B-Tree with contiguous node blocks, cache locality, and low allocator overhead |
| `metac.flat_set` | `Set` | `FlatSet<T>` | `FlatSet<T>::Range` (direct access) | ordered; contiguous sorted dynamic array with binary search lookup and cache-friendly layout |

## Maps

| Module | Type | Documented as | Range | Notes |
|---|---|---|---|---|
| `metac.chained_hash_map` | `Map` | `ChainedHashMap<K, T>` | `ChainedHashMap<K, T>::Range` (forward) | bucket chaining over an internal entry set |
| `metac.intrusive_hash_map` | `Map` | `IntrusiveHashMap<K, T>` | `IntrusiveHashMap<K, T>::Range` (forward) | flat open addressing; entries carry the sentinels |
| `metac.tree_map` | `Map` | `TreeMap<K, T>` | `TreeMap<K, T>::Range` (bidirectional) | ordered by key over a binary search tree set (@ref AVLSet, @ref RBSet, @ref TreapSet) |
| `metac.btree_map` | `Map` | `BTreeMap<K, T>` | `BTreeMap<K, T>::Range` (bidirectional) | ordered by key over an internal B-Tree set (@ref BTreeSet) |
| `metac.flat_map` | `Map` | `FlatMap<K, T>` | `FlatMap<K, T>::Range` (bidirectional) | ordered by key over a contiguous sorted array of key-value pairs (AoS) |

## Multisets

| Module | Type | Documented as | Range | Notes |
|---|---|---|---|---|
| `metac.flat_multiset` | `Set` | `FlatMultiset<T>` | `FlatMultiset<T>::Range` (direct access) | ordered; contiguous sorted dynamic array multiset with binary search and duplicates preserved |
| `metac.counter` | `Counter` | `Counter<T>` | `Counter<T>::Range` (forward) | multiset tracking element multiplicities; backed by configurable map backend |

## Multimaps

| Module | Type | Documented as | Range | Notes |
|---|---|---|---|---|
| `metac.flat_multimap` | `Map` | `FlatMultimap<K, T>` | `FlatMultimap<K, T>::Range` (forward) | ordered by key over a contiguous sorted array of key-value pairs (AoS) with duplicate keys preserved |
| `metac.multimap` | `Map` | `Multimap<K, T>` | `Multimap<K, T>::Range` (forward) | generic multimap mapping keys to multiple values; parameterized by a set and a collection container |

## Value types

| Module | Type | Documented as | Notes |
| `metac.bit_array` | `Array` | `BitArray<N>` | fixed-size inline bit array; set algebra, popcount, zero heap allocation |
| `metac.bit_vector` | `Vector` | `BitVector` | dynamically resizable packed bit vector; O(1) push/pop, set algebra |
| `metac.record` | `Record` | `Record` | user-defined aggregate of named fields, with generated getters/setters |
| `metac.variant` | `Variant` | `Variant` | union holding one value out of a predefined set of types |
| `metac.reference` | `Counted` | `Counted<T>` | reference-counted shared instance |
| `metac.reference` | `Raw` | `Raw<T>` | unmanaged handle to a manually managed instance |

## Choosing a container

1. **Do you need indexed access?** Use @ref Array when size is fixed, or @ref Vector
   for dynamic resizing (with optional small buffer optimization via inline capacity),
   or @ref Packet when capacity is bounded and zero heap allocation is required,
   or @ref TieredVector when the buffer grows large or grows often and you need stable element addresses.
2. **Do you need to insert or remove at both ends?** Use @ref Deque; the adapters
   @ref Stack and @ref Queue are the LIFO/FIFO specializations of that pattern.
3. **Do you only touch the front in FIFO-ish fashion and want minimal bookkeeping?** Use @ref List.
4. **Do you consume elements in priority order?** Use @ref PriorityQueue.
5. **Do you need uniqueness with the element's own hash and equality?** Use
   @ref ChainedHashSet (the safe default) or @ref IntrusiveHashSet when the element type can
   reserve two sentinel states and the flat layout matters.
6. **Do you need the elements in sorted order, or ordering-based queries?** Use @ref FlatSet
   for compact contiguous cache-friendly storage and fast binary search lookups (when mutations
   are infrequent), or @ref AVLSet / @ref RBSet / @ref TreapSet / @ref BTreeSet when frequent insertions and
   deletions require O(log n) tree mutations (with @ref BTreeSet providing cache-friendly node fanout).
7. **Do you map keys to values?** Pick the map in the same family as the set you would have
   picked — @ref FlatMap for cache locality and flat memory, or @ref ChainedHashMap,
   @ref IntrusiveHashMap, @ref TreeMap (parameterized by your choice of tree set backend), or @ref BTreeMap.
8. **Do you need shared ownership of an element?** Use @ref Counted (or @ref Raw for manual
   lifetime management) — both work as container elements.
9. **Do you need a compact set of flags, booleans, or small integer universe?** Use
   @ref BitArray for zero-heap, fixed-capacity bitwise set algebra, or @ref BitVector
   for dynamic runtime capacity and bitstream operations.
10. **Do you need a multiset (duplicate items allowed)?** Use @ref FlatMultiset for
    contiguous sorted dynamic array storage with binary search lookups, or @ref Counter
    to track element multiplicities over a configurable map backend (e.g. @ref FlatMap
    for cache efficiency or @ref ChainedHashMap for O(1) hash-based counting).
11. **Do you associate multiple values with each key (multimap)?** Use @ref FlatMultimap
    for contiguous sorted array storage with binary search lookups (AoS layout), or
    @ref Multimap for generic key-to-collection mapping parameterized by an underlying
    set and collection container (e.g. tree set + vector).

All concrete containers in one module share a single generated header, and each brings its
own group in this manual, so the operations of `ChainedHashSet` and `IntrusiveHashSet` never
have to be guessed: they are documented side by side.

## Optional feature groups

To reduce generated code size and eliminate unused C standard library dependencies (such as `<stdio.h>` or `<stdarg.h>`), specialized container operations are categorized into optional feature groups. By default, all optional groups are enabled (`True`) so types provide full functionality unless explicitly configured otherwise. Enclosing containers (such as maps backed by sets, or string buffers holding chunk vectors) automatically disable groups they do not use.

| Optional Group | Parameter | Containers | Methods | Description |
|---|---|---|---|---|
| Set Algebra | `algebraic_operations=True` | `Set` (`ChainedHashSet`, `IntrusiveHashSet`, `TreapSet`, `RBSet`, `AVLSet`, `FlatSet`), `Multiset` (`FlatMultiset`), `BitArray`, `BitVector`, `Counter` | `create_union`, `create_intersection`, `create_difference`, `create_symmetric_difference`, `apply_union`, `apply_intersection`, `apply_difference`, `apply_symmetric_difference`, `is_subset`, `is_superset` | Mathematical set algebra (constructing and mutating). Automatically disabled on sets used internally by maps. |
| Sorting & Search | `sorting_operations=True` | `Sortable` (`Vector`, `TieredVector`, `Array`) | `sort`, `reverse`, `sorted`, `lower_bound`, `upper_bound`, `binary_search` | Quicksort, reversal, sortedness check, and binary search algorithms. Automatically disabled on chunk vectors inside `StringBuffer`. |
| Formatted Output | `formatting_operations=True` | `String`, `StringBuffer` | `format`, `format_args`, `push_format`, `push_format_args`, `push_double`, `push_long_double` | `printf`-style formatted output and floating-point conversions, requiring `<stdio.h>` and `<stdarg.h>`. Automatically disabled on internal string instances. |

In the reference manual, every method belonging to an optional group is marked with an italic note indicating its function group (for example, *An optional operation belonging to the Sortable function group.*).