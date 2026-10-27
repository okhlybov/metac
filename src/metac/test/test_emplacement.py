from metac.test import *
from metac.test.custom_composite import Type as CustomComposite
from metac.test.cstring import cstring, s
from metac.vector import Vector
from metac.list import List
from metac.flat_map import Map as FlatMap
from metac.chained_hash_set import Set as ChainedHashSet
from metac.priority_queue import Queue as PriorityQueue
from metac.flat_multiset import Set as FlatMultiset
from metac.counter import Counter
from metac.multimap import Map as Multimap
from metac.flat_multimap import Map as FlatMultimap
from metac.array import Array
from metac.avl_set import Set as AVLSet
from metac.record import Record
from metac.variant import Variant

# 1. Vector of CustomComposite (custom create(target, value))
custom_elem = CustomComposite("custom_elem")
vec_type = Vector("custom_elem_vector", custom_elem)
x_vec = Type(vec_type, dependencies=[custom_elem])

vt = vec_type.variable("vt")
x_vec.setup(f"""
  {vt.definition};
  {vec_type.create(vt)};
""")
x_vec.cleanup(f"""
  {vec_type.destroy(vt)};
""")

x_vec.unit(f"{vec_type.emplace_back}(): emplace with constructor parameter forwarding", f"""
  {vec_type.emplace_back(vt, 42)};
  {vec_type.emplace_back(vt, 99)};
  TEST_EQUAL({vec_type.size(vt)}, 2);
  {{ custom_elem g = {vec_type.get(vt, 0)}; TEST_EQUAL(*g.value, 42); {custom_elem.destroy("&g")}; }}
  {{ custom_elem g = {vec_type.get(vt, 1)}; TEST_EQUAL(*g.value, 99); {custom_elem.destroy("&g")}; }}
""")


# 2. List of CustomComposite
list_type = List("custom_elem_list", custom_elem)
x_list = Type(list_type, dependencies=[custom_elem])

lt = list_type.variable("lt")
x_list.setup(f"""
  {lt.definition};
  {list_type.create(lt)};
""")
x_list.cleanup(f"""
  {list_type.destroy(lt)};
""")

x_list.unit(f"{list_type.emplace_front}(): emplace_front forwarding", f"""
  {list_type.emplace_front(lt, 100)};
  {list_type.emplace_front(lt, 200)};
  TEST_EQUAL({list_type.size(lt)}, 2);
  TEST_EQUAL(*{list_type.front_view(lt)}->value, 200);
""")


# 3. PriorityQueue of CustomComposite
pq_type = PriorityQueue("custom_elem_pq", custom_elem)
x_pq = Type(pq_type, dependencies=[custom_elem])

pqt = pq_type.variable("pqt")
x_pq.setup(f"""
  {pqt.definition};
  {pq_type.create(pqt)};
""")
x_pq.cleanup(f"""
  {pq_type.destroy(pqt)};
""")

x_pq.unit(f"{pq_type.emplace}(): emplace into priority queue", f"""
  {pq_type.emplace(pqt, 10)};
  {pq_type.emplace(pqt, 50)};
  {pq_type.emplace(pqt, 30)};
  TEST_EQUAL({pq_type.size(pqt)}, 3);
  TEST_EQUAL(*{pq_type.top_view(pqt)}->value, 50);
""")


# 4. FlatMap with CustomComposite values
fm_type = FlatMap("custom_elem_flat_map", custom_elem, "int")
x_fm = Type(fm_type, dependencies=[custom_elem])

fmt = fm_type.variable("fmt")
x_fm.setup(f"""
  {fmt.definition};
  {fm_type.create(fmt)};
""")
x_fm.cleanup(f"""
  {fm_type.destroy(fmt)};
""")

x_fm.unit(f"{fm_type.emplace}(): emplace into flat map forwarding value params", f"""
  int res1 = {fm_type.emplace(fmt, 1, 111)};
  int res2 = {fm_type.emplace(fmt, 2, 222)};
  int res3 = {fm_type.emplace(fmt, 1, 999)};
  TEST_EQUAL(res1, 1);
  TEST_EQUAL(res2, 1);
  TEST_EQUAL(res3, 0);
  TEST_EQUAL({fm_type.size(fmt)}, 2);
  {{ custom_elem g = {fm_type.get(fmt, 1)}; TEST_EQUAL(*g.value, 111); {custom_elem.destroy("&g")}; }}
  {{ custom_elem g = {fm_type.get(fmt, 2)}; TEST_EQUAL(*g.value, 222); {custom_elem.destroy("&g")}; }}
""")


# 5. ChainedHashSet of CustomComposite
chs_type = ChainedHashSet("custom_elem_hash_set", custom_elem)
x_chs = Type(chs_type, dependencies=[custom_elem])

chst = chs_type.variable("chst")
x_chs.setup(f"""
  {chst.definition};
  {chs_type.create(chst)};
""")
x_chs.cleanup(f"""
  {chs_type.destroy(chst)};
""")

x_chs.unit(f"{chs_type.emplace}(): emplace into hash set forwarding params", f"""
  int r1 = {chs_type.emplace(chst, 7)};
  int r2 = {chs_type.emplace(chst, 14)};
  int r3 = {chs_type.emplace(chst, 7)};
  TEST_EQUAL(r1, 1);
  TEST_EQUAL(r2, 1);
  TEST_EQUAL(r3, 0);
  TEST_EQUAL({chs_type.size(chst)}, 2);
""")


# 6. FlatMultiset of CustomComposite - emplace always inserts, duplicates preserved
fms_type = FlatMultiset("custom_elem_flat_multiset", custom_elem)
x_fms = Type(fms_type, dependencies=[custom_elem])

fmst = fms_type.variable("fmst")
x_fms.setup(f"""
  {fmst.definition};
  {fms_type.create(fmst)};
""")
x_fms.cleanup(f"""
  {fms_type.destroy(fmst)};
""")

x_fms.unit(f"{fms_type.emplace}(): emplace into flat multiset keeping duplicates", f"""
  int r1 = {fms_type.emplace(fmst, 7)};
  int r2 = {fms_type.emplace(fmst, 7)};
  TEST_EQUAL(r1, 1);
  TEST_EQUAL(r2, 1);
  TEST_EQUAL({fms_type.size(fmst)}, 2);
  {{ custom_elem e7; {custom_elem.create("&e7", 7)};
     TEST_EQUAL({fms_type.count(fmst, "&e7")}, 2);
     {custom_elem.destroy("&e7")}; }}
""")


# 7. Counter of CustomComposite - emplace adds the constructed element once
ct_type = Counter("custom_elem_counter", custom_elem, backend=FlatMap)
x_ct = Type(ct_type, dependencies=[custom_elem])

ctt = ct_type.variable("ctt")
x_ct.setup(f"""
  {ctt.definition};
  {ct_type.create(ctt)};
""")
x_ct.cleanup(f"""
  {ct_type.destroy(ctt)};
""")

x_ct.unit(f"{ct_type.emplace}(): emplace into counter", f"""
  {ct_type.emplace(ctt, 5)};
  {{ custom_elem e5; {custom_elem.create("&e5", 5)};
     TEST_EQUAL({ct_type.count(ctt, "&e5")}, 1);
     {custom_elem.destroy("&e5")}; }}
  TEST_EQUAL({ct_type.total_size(ctt)}, 1);
  TEST_EQUAL({ct_type.distinct_size(ctt)}, 1);
""")


# 8. Generic Multimap of CustomComposite values over int keys
mm_type = Multimap("custom_elem_multimap", custom_elem, "int", AVLSet, Vector)
x_mm = Type(mm_type, dependencies=[custom_elem])

mmt = mm_type.variable("mmt")
x_mm.setup(f"""
  {mmt.definition};
  {mm_type.create(mmt)};
""")
x_mm.cleanup(f"""
  {mm_type.destroy(mmt)};
""")

x_mm.unit(f"{mm_type.emplace}(): emplace into multimap forwarding value params", f"""
  int r1 = {mm_type.emplace(mmt, 1, 111)};
  int r2 = {mm_type.emplace(mmt, 1, 222)};
  TEST_EQUAL(r1, 1);
  TEST_EQUAL(r2, 1);
  TEST_EQUAL({mm_type.count(mmt, 1)}, 2);
  TEST_EQUAL(*{mm_type.view(mmt, 1)}->value, 111);
""")


# 9. FlatMultimap of CustomComposite values
fmm_type = FlatMultimap("custom_elem_flat_multimap", custom_elem, "int")
x_fmm = Type(fmm_type, dependencies=[custom_elem])

fmmt = fmm_type.variable("fmmt")
x_fmm.setup(f"""
  {fmmt.definition};
  {fmm_type.create(fmmt)};
""")
x_fmm.cleanup(f"""
  {fmm_type.destroy(fmmt)};
""")

x_fmm.unit(f"{fmm_type.emplace}(): emplace into flat multimap forwarding value params", f"""
  int r1 = {fmm_type.emplace(fmmt, 1, 111)};
  TEST_EQUAL(r1, 1);
  TEST_EQUAL({fmm_type.count(fmmt, 1)}, 1);
  TEST_EQUAL(*{fmm_type.view(fmmt, 1)}->value, 111);
""")


# 10. Array of cstring - fixed capacity, emplace destroys the previous element in place
arr_type = Array("emplace_str_array", cstring, 4)
x_arr = Type(arr_type, dependencies=[cstring])

at = arr_type.variable("at")
x_arr.setup(f"""
  {at.definition};
  {arr_type.create(at)};
""")
x_arr.cleanup(f"""
  {arr_type.destroy(at)};
""")

x_arr.unit(f"{arr_type.emplace}(): emplace into array destroying the previous element", f"""
  {arr_type.set(at, 1, s("hello"))};
  TEST_EQUAL_CHARS({arr_type.view(at, 1)}, "hello");
  {arr_type.emplace(at, 1)};
  TEST_EQUAL_CHARS({arr_type.view(at, 1)}, "");
""")


# 11. Record - per-field in-place construction (fields must default-construct for create())
rec_type = Record("emplace_record", {"tag": "int", "text": cstring})
x_rec = Type(rec_type, dependencies=[cstring])

rt = rec_type.variable("rt")
x_rec.setup(f"""
  {rt.definition};
  {rec_type.create(rt)};
""")
x_rec.cleanup(f"""
  {rec_type.destroy(rt)};
""")

x_rec.unit(f"{rec_type.emplace_text}(): construct record field in place", f"""
  {rec_type.set_tag(rt, 7)};
  {rec_type.set_text(rt, s("hello"))};
  TEST_EQUAL(rt.tag, 7);
  TEST_EQUAL_CHARS(rt.text, "hello");
  {rec_type.emplace_tag(rt)};
  {rec_type.emplace_text(rt)};
  TEST_EQUAL(rt.tag, 0);
  TEST_EQUAL_CHARS(rt.text, "");
""")


# 12. Variant with a CustomComposite alternative - per-alternative in-place construction
var_type = Variant("custom_elem_variant", {"num": "int", "box": custom_elem})
x_var = Type(var_type, dependencies=[custom_elem])

vt = var_type.variable("vt")
x_var.setup(f"""
  {vt.definition};
  {var_type.create(vt)};
""")
x_var.cleanup(f"""
  {var_type.destroy(vt)};
""")

x_var.unit(f"{var_type.emplace_box}(): construct variant alternative in place", f"""
  {var_type.emplace_box(vt, 42)};
  TEST_TRUE({var_type.is_box(vt)});
  TEST_EQUAL(*{var_type.get_box_view(vt)}->value, 42);
  {var_type.emplace_num(vt)};
  TEST_TRUE({var_type.is_num(vt)});
  TEST_EQUAL({var_type.get_num(vt)}, 0);
""")
