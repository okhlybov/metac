from autoc.test import *
from autoc.vector import Vector
from autoc.array import Array
from autoc.tiered_vector import Vector as TieredVector
from autoc.chained_hash_set import Set as ChainedHashSet
from autoc.chained_hash_map import Map as ChainedHashMap
from autoc.treap_set import Set as TreapSet
from autoc.tree_map import Map as TreeMap
from autoc.bit_array import Array as BitArray
from autoc.bit_vector import Vector as BitVector
from autoc.string import String
from autoc.string_buffer import Buffer as StringBuffer
from autoc.counter import Counter
from autoc.flat_multiset import Set as FlatMultiset
import autoc.flat_map


# 1. Verify sorting_operations on Vector, TieredVector, and Array
v_nosort = Vector("v_nosort", "int", sorting_operations=False)
assert not v_nosort.sort.active
assert not v_nosort.reverse.active
assert not v_nosort.sorted.active
assert not v_nosort.binary_search.active
assert not v_nosort.lower_bound.active
assert not v_nosort.upper_bound.active
assert v_nosort.push.active
assert v_nosort.pop.active
assert v_nosort.size.active

v_sort = Vector("v_sort", "int")
assert v_sort.sort.active
assert v_sort.reverse.active
assert v_sort.sorted.active
assert v_sort.binary_search.active

tv_nosort = TieredVector("tv_nosort", "int", sorting_operations=False)
assert not tv_nosort.sort.active
assert not tv_nosort.reverse.active
assert not tv_nosort.sorted.active
assert not tv_nosort.binary_search.active
assert tv_nosort.push.active

arr_nosort = Array("arr_nosort", "int", 8, sorting_operations=False)
assert not arr_nosort.sort.active
assert not arr_nosort.reverse.active
assert not arr_nosort.sorted.active
assert not arr_nosort.binary_search.active
assert arr_nosort.get.active
assert arr_nosort.set.active

arr_sort = Array("arr_sort", "int", 8)
assert arr_sort.sort.active
assert arr_sort.reverse.active
assert arr_sort.sorted.active


# 2. Verify algebraic_operations on ChainedHashSet, TreapSet, and BitSet
s_noalg = ChainedHashSet("s_noalg", "int", algebraic_operations=False)
assert not s_noalg.apply_union.active
assert not s_noalg.apply_difference.active
assert not s_noalg.apply_intersection.active
assert not s_noalg.apply_symmetric_difference.active
assert not s_noalg.create_union.active
assert not s_noalg.create_difference.active
assert not s_noalg.create_intersection.active
assert not s_noalg.create_symmetric_difference.active
assert not s_noalg.is_subset.active
assert not s_noalg.is_superset.active
assert s_noalg.put.active
assert s_noalg.remove.active
assert s_noalg.contains.active

s_alg = ChainedHashSet("s_alg", "int")
assert s_alg.apply_union.active
assert s_alg.create_union.active
assert s_alg.is_subset.active

ts_noalg = TreapSet("ts_noalg", "int", algebraic_operations=False)
assert not ts_noalg.apply_union.active
assert not ts_noalg.apply_difference.active
assert not ts_noalg.apply_intersection.active
assert not ts_noalg.apply_symmetric_difference.active
assert not ts_noalg.create_union.active
assert not ts_noalg.create_difference.active
assert not ts_noalg.create_intersection.active
assert not ts_noalg.create_symmetric_difference.active
assert ts_noalg.put.active
assert ts_noalg.contains.active

fms_noalg = FlatMultiset("fms_noalg", "int", algebraic_operations=False)
assert not fms_noalg.apply_union.active
assert not fms_noalg.apply_difference.active
assert not fms_noalg.apply_intersection.active
assert not fms_noalg.apply_symmetric_difference.active
assert not fms_noalg.create_union.active
assert not fms_noalg.create_difference.active
assert not fms_noalg.create_intersection.active
assert not fms_noalg.create_symmetric_difference.active
assert not fms_noalg.is_subset.active
assert not fms_noalg.is_superset.active
assert fms_noalg.put.active
assert fms_noalg.remove.active
assert fms_noalg.wipe.active
assert fms_noalg.count.active

fms_alg = FlatMultiset("fms_alg", "int")
assert fms_alg.apply_union.active
assert fms_alg.apply_difference.active
assert fms_alg.apply_intersection.active
assert fms_alg.apply_symmetric_difference.active
assert fms_alg.create_union.active
assert fms_alg.create_difference.active
assert fms_alg.create_intersection.active
assert fms_alg.create_symmetric_difference.active
assert fms_alg.is_subset.active
assert fms_alg.is_superset.active
assert fms_alg.apply_union.optional_group == "algebraic_operations"
assert fms_alg.create_union.optional_group == "algebraic_operations"


ba_noalg = BitArray("ba_noalg", 32, algebraic_operations=False)
assert not ba_noalg.apply_union.active
assert not ba_noalg.apply_intersection.active
assert not ba_noalg.apply_difference.active
assert not ba_noalg.apply_symmetric_difference.active
assert not ba_noalg.create_union.active
assert not ba_noalg.create_intersection.active
assert not ba_noalg.create_difference.active
assert not ba_noalg.create_symmetric_difference.active
assert not ba_noalg.is_subset.active
assert ba_noalg.test.active
assert ba_noalg.set.active
assert ba_noalg.count.active

ba_alg = BitArray("ba_alg", 32)
assert ba_alg.apply_union.active
assert ba_alg.create_union.active
assert ba_alg.is_subset.active

bv_noalg = BitVector("bv_noalg", algebraic_operations=False)
assert not bv_noalg.apply_union.active
assert not bv_noalg.apply_intersection.active
assert not bv_noalg.apply_difference.active
assert not bv_noalg.apply_symmetric_difference.active
assert not bv_noalg.create_union.active
assert not bv_noalg.create_intersection.active
assert not bv_noalg.create_difference.active
assert not bv_noalg.create_symmetric_difference.active
assert not bv_noalg.is_subset.active
assert bv_noalg.test.active
assert bv_noalg.set.active
assert bv_noalg.count.active

bv_alg = BitVector("bv_alg")
assert bv_alg.apply_union.active
assert bv_alg.create_union.active
assert bv_alg.is_subset.active

cnt_noalg = Counter("cnt_noalg", "int", autoc.flat_map.Map, algebraic_operations=False)
assert not cnt_noalg.apply_union.active
assert not cnt_noalg.apply_intersection.active
assert not cnt_noalg.apply_difference.active
assert not cnt_noalg.apply_symmetric_difference.active
assert not cnt_noalg.create_union.active
assert not cnt_noalg.create_intersection.active
assert not cnt_noalg.create_difference.active
assert not cnt_noalg.create_symmetric_difference.active
assert not cnt_noalg.is_subset.active
assert cnt_noalg.add.active
assert cnt_noalg.remove.active
assert cnt_noalg.count.active

cnt_alg = Counter("cnt_alg", "int", autoc.flat_map.Map)
assert cnt_alg.apply_union.active
assert cnt_alg.apply_intersection.active
assert cnt_alg.apply_difference.active
assert cnt_alg.apply_symmetric_difference.active
assert cnt_alg.create_union.active
assert cnt_alg.create_intersection.active
assert cnt_alg.create_difference.active
assert cnt_alg.create_symmetric_difference.active
assert cnt_alg.is_subset.active


# 3. Verify formatting_operations on String and StringBuffer
str_noformat = String("str_noformat", formatting_operations=False)
assert not str_noformat.format.active
assert not str_noformat.format_args.active
assert str_noformat.size.active
assert str_noformat.new.active

str_format = String("str_format")
assert str_format.format.active
assert str_format.format_args.active

sbuf_noformat = StringBuffer("sbuf_noformat", formatting_operations=False)
assert not sbuf_noformat.push_format.active
assert not sbuf_noformat.push_format_args.active
assert not sbuf_noformat.push_double.active
assert not sbuf_noformat.push_long_double.active
assert sbuf_noformat.push.active
assert sbuf_noformat.push_slice.active
assert sbuf_noformat.push_char.active
assert sbuf_noformat.push_int.active

sbuf_format = StringBuffer("sbuf_format")
assert sbuf_format.push_format.active
assert sbuf_format.push_double.active


# 4. Verify enclosing consumers explicitly set disabled features
cmap = ChainedHashMap("cmap_test", "int", "int")
assert cmap._set.algebraic_operations is False
assert not cmap._set.apply_union.active
assert not cmap._set.create_union.active
assert not cmap._set.is_subset.active

tmap = TreeMap("tmap_test", "int", "int", TreapSet)
assert tmap._set.algebraic_operations is False
assert not tmap._set.apply_union.active
assert not tmap._set.create_union.active

sbuf = StringBuffer("sbuf_test")
assert sbuf._string.formatting_operations is False
assert not sbuf._string.format.active
assert sbuf._chunks.sorting_operations is False
assert not sbuf._chunks.sort.active


# 5. C execution tests for types generated with disabled features
xv = Type(type_v := Vector("opt_int_vector", "int", sorting_operations=False))
tv = type_v.variable("tv")
xv.setup(f"""
  {tv.definition};
  {type_v.create(tv)};
""")
xv.cleanup(f"""
  {type_v.destroy(tv)};
""")
xv.unit(f"{type_v}: operations work when sorting is disabled", f"""
  {type_v.push(tv, 10)};
  {type_v.push(tv, 20)};
  {type_v.push(tv, 30)};
  TEST_EQUAL( {type_v.size(tv)}, 3 );
  TEST_EQUAL( {type_v.get(tv, 0)}, 10 );
  TEST_EQUAL( {type_v.get(tv, 1)}, 20 );
  TEST_EQUAL( {type_v.get(tv, 2)}, 30 );
  TEST_EQUAL( {type_v.pop(tv)}, 30 );
  TEST_EQUAL( {type_v.size(tv)}, 2 );
""")

xba = Type(type_ba := BitArray("opt_bitarray", 16, algebraic_operations=False))
tba = type_ba.variable("tba")
xba.setup(f"""
  {tba.definition};
  {type_ba.create(tba)};
""")
xba.unit(f"{type_ba}: bit array operations work when algebra is disabled", f"""
  {type_ba.set(tba, 3)};
  {type_ba.set(tba, 7)};
  TEST_TRUE( {type_ba.test(tba, 3)} );
  TEST_TRUE( {type_ba.test(tba, 7)} );
  TEST_FALSE( {type_ba.test(tba, 5)} );
  TEST_EQUAL( {type_ba.count(tba)}, 2 );
  {type_ba.clear(tba, 3)};
  TEST_FALSE( {type_ba.test(tba, 3)} );
  TEST_EQUAL( {type_ba.count(tba)}, 1 );
""")

xsb = Type(type_sb := StringBuffer("opt_string_buffer", formatting_operations=False))
tsb = type_sb.variable("tsb")
xsb.setup(f"""
  {tsb.definition};
  {type_sb.create(tsb)};
""")
xsb.cleanup(f"""
  {type_sb.destroy(tsb)};
""")
xsb.unit(f"{type_sb}: string buffer works when formatting is disabled", f"""
  {type_sb.push(tsb, '"Hello "')};
  {type_sb.push_char(tsb, "'W'")};
  {type_sb.push(tsb, '"orld"')};
  {type_sb.push_int(tsb, 42)};
  TEST_EQUAL_CHARS( {type_sb.view(tsb)}, "Hello World42" );
""")


# 6. Verify optional_group metadata and documentation notes on methods
assert v_sort.sort.optional_group == "sorting_operations"
assert v_sort.reverse.optional_group == "sorting_operations"
assert v_sort.sorted.optional_group == "sorting_operations"
assert v_sort.binary_search.optional_group == "sorting_operations"
assert v_sort.lower_bound.optional_group == "sorting_operations"
assert v_sort.upper_bound.optional_group == "sorting_operations"
assert v_sort.push.optional_group is None

assert s_alg.apply_union.optional_group == "algebraic_operations"
assert s_alg.apply_difference.optional_group == "algebraic_operations"
assert s_alg.apply_intersection.optional_group == "algebraic_operations"
assert s_alg.apply_symmetric_difference.optional_group == "algebraic_operations"
assert s_alg.create_union.optional_group == "algebraic_operations"
assert s_alg.create_difference.optional_group == "algebraic_operations"
assert s_alg.create_intersection.optional_group == "algebraic_operations"
assert s_alg.create_symmetric_difference.optional_group == "algebraic_operations"
assert s_alg.is_subset.optional_group == "algebraic_operations"
assert s_alg.is_superset.optional_group == "algebraic_operations"
assert s_alg.put.optional_group is None

assert ba_alg.apply_union.optional_group == "algebraic_operations"
assert ba_alg.apply_intersection.optional_group == "algebraic_operations"
assert ba_alg.apply_difference.optional_group == "algebraic_operations"
assert ba_alg.apply_symmetric_difference.optional_group == "algebraic_operations"
assert ba_alg.create_union.optional_group == "algebraic_operations"
assert ba_alg.create_intersection.optional_group == "algebraic_operations"
assert ba_alg.create_difference.optional_group == "algebraic_operations"
assert ba_alg.create_symmetric_difference.optional_group == "algebraic_operations"
assert ba_alg.is_subset.optional_group == "algebraic_operations"
assert ba_alg.test.optional_group is None

assert bv_alg.apply_union.optional_group == "algebraic_operations"
assert bv_alg.apply_intersection.optional_group == "algebraic_operations"
assert bv_alg.apply_difference.optional_group == "algebraic_operations"
assert bv_alg.apply_symmetric_difference.optional_group == "algebraic_operations"
assert bv_alg.create_union.optional_group == "algebraic_operations"
assert bv_alg.create_intersection.optional_group == "algebraic_operations"
assert bv_alg.create_difference.optional_group == "algebraic_operations"
assert bv_alg.create_symmetric_difference.optional_group == "algebraic_operations"
assert bv_alg.is_subset.optional_group == "algebraic_operations"
assert bv_alg.test.optional_group is None

assert cnt_alg.apply_union.optional_group == "algebraic_operations"
assert cnt_alg.apply_intersection.optional_group == "algebraic_operations"
assert cnt_alg.apply_difference.optional_group == "algebraic_operations"
assert cnt_alg.apply_symmetric_difference.optional_group == "algebraic_operations"
assert cnt_alg.create_union.optional_group == "algebraic_operations"
assert cnt_alg.create_intersection.optional_group == "algebraic_operations"
assert cnt_alg.create_difference.optional_group == "algebraic_operations"
assert cnt_alg.create_symmetric_difference.optional_group == "algebraic_operations"
assert cnt_alg.is_subset.optional_group == "algebraic_operations"
assert cnt_alg.add.optional_group is None

assert str_format.format.optional_group == "formatting_operations"
assert str_format.format_args.optional_group == "formatting_operations"

assert sbuf_format.push_format.optional_group == "formatting_operations"
assert sbuf_format.push_format_args.optional_group == "formatting_operations"
assert sbuf_format.push_double.optional_group == "formatting_operations"
assert sbuf_format.push_long_double.optional_group == "formatting_operations"
assert sbuf_format.push.optional_group is None

# Verify documentation comment rendering contains optional group note
stream = []
v_sort.sort._render_documentation(stream, True)
rendered_doc = str().join(stream)
assert "_An optional operation belonging to the Sortable function group._" in rendered_doc

stream = []
s_alg.apply_union._render_documentation(stream, True)
rendered_doc = str().join(stream)
assert "_An optional operation belonging to the AlgebraicSet function group._" in rendered_doc

stream = []
sbuf_format.push_format._render_documentation(stream, True)
rendered_doc = str().join(stream)
assert "_An optional operation belonging to the Formatting function group._" in rendered_doc


# 7. Verify function-level references and dependencies of formatting and wrapper methods
import autoc.std as std

# String.format references format_args (no ordering dependency on format_args, depends only on stdarg.h)
assert str_format.format_args in str_format.format.references
assert str_format.format_args not in str_format.format.dependencies
assert std.stdarg_h in str_format.format.dependencies
assert std.stdio_h not in str_format.format.dependencies
assert std.stdio_h in str_format.format_args.dependencies

# StringBuffer.push_format references push_format_args (no ordering dependency, depends only on stdarg.h)
assert sbuf_format.push_format_args in sbuf_format.push_format.references
assert sbuf_format.push_format_args not in sbuf_format.push_format.dependencies
assert std.stdarg_h in sbuf_format.push_format.dependencies
assert std.stdio_h not in sbuf_format.push_format.dependencies
assert std.stdio_h in sbuf_format.push_format_args.dependencies

# StringBuffer.push_double / push_long_double reference push_format without header dependencies
assert sbuf_format.push_format in sbuf_format.push_double.references
assert sbuf_format.push_format not in sbuf_format.push_double.dependencies
assert std.stdio_h not in sbuf_format.push_double.dependencies
assert sbuf_format.push_format in sbuf_format.push_long_double.references
assert sbuf_format.push_format not in sbuf_format.push_long_double.dependencies
assert std.stdio_h not in sbuf_format.push_long_double.dependencies

# StringBuffer integer and slice wrappers use references
assert sbuf_format.push_slice in sbuf_format.push.references
assert sbuf_format.push_slice not in sbuf_format.push.dependencies
assert sbuf_format.push_ulong in sbuf_format.push_uint.references
assert sbuf_format.push_ulong not in sbuf_format.push_uint.dependencies
assert sbuf_format.push_long in sbuf_format.push_int.references
assert sbuf_format.push_long not in sbuf_format.push_int.dependencies
assert sbuf_format.push_slice in sbuf_format.push_ulong.references
assert sbuf_format.push_slice in sbuf_format.push_long.references
assert sbuf_format.view in sbuf_format.take.references
assert sbuf_format.view not in sbuf_format.take.dependencies

# Sortable wrappers use references
assert v_sort.sort_range in v_sort.sort.references
assert v_sort.sort_range not in v_sort.sort.dependencies
assert v_sort.sort_insertion in v_sort.sort_range.references
assert v_sort.sort_insertion not in v_sort.sort_range.dependencies
assert v_sort.lower_bound in v_sort.binary_search.references
assert v_sort.lower_bound not in v_sort.binary_search.dependencies

# Array wrappers use references
assert arr_sort.get in arr_sort.front.references
assert arr_sort.get not in arr_sort.front.dependencies
assert arr_sort.view in arr_sort.front_view.references
assert arr_sort.view not in arr_sort.front_view.dependencies
assert arr_sort.get in arr_sort.back.references
assert arr_sort.get not in arr_sort.back.dependencies
assert arr_sort.view in arr_sort.back_view.references
assert arr_sort.view not in arr_sort.back_view.dependencies

# Sortable and Searchable operations hardcode size_t for array positions
assert v_sort.lower_bound.result == std.size_t
assert v_sort.upper_bound.result == std.size_t
assert v_sort.sort_insertion.arguments[1].type == std.size_t
assert v_sort.sort_insertion.arguments[2].type == std.size_t
assert v_sort.sort_range.arguments[1].type == std.size_t
assert v_sort.sort_range.arguments[2].type == std.size_t

# FlatSet has no index attribute and its search operations return size_t
from autoc.flat_set import Set as FlatSet
fs = FlatSet("fs", "int")
assert not hasattr(fs, "index")
assert fs.lower_bound.result == std.size_t
assert fs.upper_bound.result == std.size_t

