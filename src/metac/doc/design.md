# Design principles {#design}

`metac` is small enough that its whole behaviour can be described by one protocol, one range
abstraction and a handful of container strategies. This chapter explains the ideas the
reference manual assumes.

## The value-semantics protocol

Everything `metac` generates — containers, records, references, variants — is a *value type*
with a regular representation. Concretely, a type `T` implements as many of these operations
as its element types allow:

| Operation | Contract |
|---|---|
| `T_create(T* target)` | leave `target` in a valid, empty/default state |
| `T_destroy(T* target)` | release the resources owned by `target` |
| `T_copy(T* target, const T* source)` | make `target` an independent duplicate of `source` |
| `T_move(T* target, T* source)` | transfer ownership to `target`; leave `source` pristine |
| `T_swap(T* left, T* right)` | exchange the representations of two complete values |
| `T_equal(const T* l, const T* r)` | equality, `int` result |
| `T_compare(const T* l, const T* r)` | ordering, negative/zero/positive `int` result |
| `T_hash(const T* target)` | hash value consistent with `T_equal` |

The operations are *derived from the presence of the definitions*: a type carries exactly the
operations it can actually implement and nothing else. A container of a non-copyable element
is itself non-copyable; a set of a non-hashable element has no `hash`. The reference manual
shows these conditional operations too — where an operation is inapplicable it simply does
not appear.

Two weaker traits relieve the pressure on element types:

- **Zero-initializability.** If the all-zero representation of the type is a valid pristine
  state, bulk allocation can default-construct by zeroing memory instead of running a loop.
- **Swappability.** Swapping is defined even for ranges and other non-owning cursors, where
  it is indistinguishable from copying, and is used to derive the move.

The **move is derived** whenever the type can manufacture a pristine shell (default
construction) and exchange representations (swap): `move` becomes *create-then-swap*. Types
with a cheaper transfer supply their own. This is why `derived_move`-style types work with no
explicit `move` at all.

## Ranges

Iteration is expressed with *ranges*: small, non-owning, copyable cursors over a container.
Every sequence and every set and map has a nested range type, named after the container —
`List<T>::Range` for @ref List, `ChainedHashMap<K, T>::Range` for @ref ChainedHashMap — with
the C spelling `ListRange`, `ChainedHashMapRange`.

A range exposes exactly the operations its access pattern supports:

| Range kind | Operations |
|---|---|
| `Input` | `empty`, `front`, `front_view`, `move_front` |
| `Forward` | adds `copy` — the cursor can be duplicated and kept |
| `Backward` | adds `back`, `back_view`, `move_back` |
| `Bidirectional` | forward and backward |
| `DirectAccess` | adds `get`/`view`/`size` — random access |

A range records *where* a traversal is, never *what* it owns: copying a range gives you an
independent iteration position, and the underlying container must outlive every range over
it. Because ranges implement the value protocol, they compose — a vector sort walks a range,
a set algorithm drains the range of its operand.

## Containers

### Capability protocols

Every container is a value type carrying the operations its element types allow; on top of
that, containers compose *capability mixins* — each declares one addressing or traversal
scheme, and a container mixes in exactly the schemes it honors:

| Concept | Kind | Operations | Semantics |
|---|---|---|---|
| `Traversable` | ability | provides `find_view`/`hash` over the range | exposes a range — the container-side counterpart of the range-directionality axis (`Forward`/`Bidirectional`/`DirectAccess` describe the cursor, `Traversable` describes the container) |
| `Sequential` | ability | adds order-sensitive `equal` | an ordered series of elements — iteration order is canonical; requires `Traversable` |
| `Insertable` | ability | `put`/`remove` | element-addressed insertion and removal — the membership addressing scheme |
| `Indexable` | ability | `indexed`/`get`/`view` | position- or key-addressed reads |
| `Assignable` | ability | adds `set` | position-addressed assignment; implies `Indexable` |
| `Sortable`, `Bisectable` | ability | `sort`/`reverse`/`sorted`, `lower_bound`/`upper_bound`/`binary_search` | user-sortable then bisectable operation groups |
| `Ordered` | property | — | born-sorted iteration: the ascending element or index order is a structural invariant, so backward traversal is available unconditionally; claimed by the tree and flat sets and the map families keyed over them, never by the hash-based families |
| `Hashed` | property | — | hash-addressed storage: elements or keys are addressed via hash digest; enforces hashability of the element or index centrally; claimed by the chained and intrusive hash sets and hash maps |

The word class carries the role: **abilities** (the `-able` family) state what a container can do and
are claimed in its bases; **properties** (the `-ed` family, `Ordered` and `Hashed` being the first) state what a
container or component *is* — and a property becomes a *requirement* the moment a composite demands
it of a component, which is expressed and enforced at the demanding container's construction time.
The demand is integrated directly into Python's typing system using annotations validated at construction
or call time via `@enforced` — through trait protocols (`Comparable`, `Orderable`, `Hashable`, etc.), compound
intersection types (`Set & Ordered`, `Sequential & Insertable`), property invariants (`Ordered`, `Hashed`), and
explicit type coercions (`Coerce[Comparable]`, `Type[Orderable]`). Requirements are checked eagerly and can be
asserted symmetrically via receiver-oriented methods (`backend.require(Ordered)`, `element.require(Comparable)`),
contract methods (`Comparable.require(element)`, `(Set & Ordered).require(backend)`), or canonical functions
(`require(target, contract)`). Violations raise `TraitError` with parameter-targeted diagnostics. The bool queries
stay total so the late-bound constraints can probe them and omit the operation rather than fail. The `Ordered` and
`Hashed` properties own their invariants centrally: every claiming container has the orderability or hashability of
its subject (the element, or the index for the keyed containers via `_ordering()` / `_hashing()`) enforced in the
property's own setup, not re-stated per concrete class. Hard element, index and backend requirements are likewise checked
in the constructors — a set demands equality-comparable elements, the hash families demand hashable
ones, the ordered trees and flat containers demand orderable ones, the adapters demand the backend
classes — so a misfit fails with a named diagnostic at composition, not as a broken render or a
missing operation minutes later. Trait-conditional operations stay constraint-gated as ever: the
constructor checks the requirements without which the container is meaningless, never the mere
absence of an optional operation.

Insertion is not one capability but a family indexed by the addressing scheme — element
(`Insertable`), position (`Assignable`), key (the `Mapping`/`Multimapping` families declare
their own keyed `put`/`set`/`emplace`/`remove`). This is why fixed-count containers (`Array`)
and specialized sequences (`String`) simply do not mix `Insertable` in rather than disabling
it, and why a map's keyed `put` does not conflict with an insertable collection's
`put(element)`: they live on disjoint branches.

Capabilities compose across containment boundaries by *static derivation*: when a container adapts
another (a map over an internal set), the adapter's capabilities follow from the component's class,
selected per concrete module — never recovered by probing the built component's instances at setup
time. A runtime type-test necessity is the taxonomy admitting a concept is missing; `Ordered` exists
precisely so that the ordered-map range kind needs no selector.

The capability claims are honest by construction. @ref PriorityQueue exposes no range at
all — its heap shape is internal — so it is `Insertable` without being `Traversable` and
defines neither equality nor hashing. Conversely, bounded containers like the circular
buffers *are* `Insertable` (bounded insertion mutates the count) while @ref Array is not
(its count is constant).

Two usage regimes of `Bisectable` exist: the flat sets and multisets are born sorted and
take the bisection operations directly (their insertion itself bisects), while the sortable
sequences mix `Sortable`, which implies `Bisectable` — the operations become meaningful
after `sort()`.

Capabilities come in two tiers. *Structural* abilities (`Traversable`, `Sequential`,
`Insertable`, `Indexable`, `Assignable`) and properties (`Ordered`, `Hashed`) are claimed by mixin
presence and cannot be switched off — a container either has a range or is born sorted or
does not. *Algorithmic conveniences* (`Sortable`/`Bisectable`, the set algebra, string
formatting) ride the operation-group flags (`sorting_operations`, `algebraic_operations`,
`formatting_operations`) so a concrete instantiation omits the code it does not need. The
third tier is not about generating code but about refusing it: *requirements* are checked
eagerly in the constructors, as described above.

### Strategies

The container strategies differ in what they guarantee, not just in performance:

- **Chained hash** (@ref ChainedHashSet, @ref ChainedHashMap) stores each element in a node
  reached from a bucket. There are no sentinel values, element addresses are stable across
  insertions, and the default hash and equality of the element are used. This is the safe
  default.
- **Open addressing** (@ref IntrusiveHashSet, @ref IntrusiveHashMap) stores the elements flat
  and marks empty and deleted slots with sentinel values supplied by the element type. It is
  the most cache-friendly layout, at the cost of requiring the element to reserve two
  distinguishable states.
- **Binary search trees** (@ref AVLSet, @ref RBSet, @ref TreapSet, @ref TreeMap) are ordered containers:
  they iterate in sorted order, support ordering-based operations and provide
  `O(log n)` insert, erase and search. The maps over trees support lexicographic
  comparison.
- **Sequences** (@ref List, @ref Deque, @ref Vector, @ref TieredVector) trade access pattern
  against allocation behaviour: forward-linked, doubly-linked, contiguous and chunked
  respectively. @ref Array and @ref String are sequences too — fixed-count and
  char-specialized respectively — which iterate but do not insert single elements.
  The bounded @ref CircularBuffer composes the full positional capability set including
  sorting. @ref PriorityQueue is a binary heap which consumes its elements in priority
  order.

## Memory, hashing and determinism

- **Memory is explicit.** Containers allocate through a manager; the generated code uses
  `malloc`/`free` with no global allocator state, so several modules can coexist.
- **Hashing is incremental.** Container hashes combine element hashes through a seeded,
  order-sensitive (or order-insensitive for unordered containers) accumulator, so the hash of
  a container reflects the hashes of its elements.
- **Generation is deterministic.** Entities are emitted in a stable topological order, so
  re-running the generator over unchanged definitions produces identical output. This is what
  makes the digest-based regeneration in `add_metac_module()` reliable.
- **References are optional.** @ref Counted provides reference counting for shared instances;
  @ref Raw is a plain unmanaged pointer. Both speak the same value protocol as everything
  else, so they can be container elements.