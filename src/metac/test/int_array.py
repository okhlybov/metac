from metac.test import *
from metac.array import Array

x = Type(type := Array("int_array", "int", 4))

t = type.variable("t")
t1 = type.variable("t1")
t2 = type.variable("t2")
r = type.range.variable("r")


x.setup(f"""
  {t.definition};
  {type.create(t)};
""")
x.cleanup(f"""
  {type.destroy(t) if type.destructible else str()}
""")

x.unit(f"{type.empty}(): test array empty and size", f"""
  TEST_FALSE( {type.empty(t)} );
  TEST_EQUAL( {type.size(t)}, 4 );
  TEST_TRUE( {type.indexed(t, 0)} );
  TEST_TRUE( {type.indexed(t, 3)} );
  TEST_FALSE( {type.indexed(t, 4)} );
""")

x.unit(f"{type.create}(): elements are default initialized to zero", f"""
  TEST_EQUAL( {type.get(t, 0)}, 0 );
  TEST_EQUAL( {type.get(t, 1)}, 0 );
  TEST_EQUAL( {type.get(t, 2)}, 0 );
  TEST_EQUAL( {type.get(t, 3)}, 0 );
""")

x.unit(f"{type.set}(), {type.get}(), {type.view}(): set and access elements", f"""
  {type.set(t, 0, 10)};
  {type.set(t, 1, 20)};
  {type.set(t, 2, 30)};
  {type.set(t, 3, 40)};
  TEST_EQUAL( {type.get(t, 0)}, 10 );
  TEST_EQUAL( {type.get(t, 1)}, 20 );
  TEST_EQUAL( {type.get(t, 2)}, 30 );
  TEST_EQUAL( {type.get(t, 3)}, 40 );
  TEST_EQUAL( *{type.view(t, 0)}, 10 );
  TEST_EQUAL( *{type.view(t, 1)}, 20 );
  TEST_EQUAL( *{type.view(t, 2)}, 30 );
  TEST_EQUAL( *{type.view(t, 3)}, 40 );
""")

x.unit(f"{type.front}(), {type.back}(): front and back access", f"""
  {type.set(t, 0, 11)};
  {type.set(t, 3, 99)};
  TEST_EQUAL( {type.front(t)}, 11 );
  TEST_EQUAL( *{type.front_view(t)}, 11 );
  TEST_EQUAL( {type.back(t)}, 99 );
  TEST_EQUAL( *{type.back_view(t)}, 99 );
""")

x.unit(f"{type.fill}(): fill all elements with a single value", f"""
  {type.fill(t, 42)};
  TEST_EQUAL( {type.get(t, 0)}, 42 );
  TEST_EQUAL( {type.get(t, 1)}, 42 );
  TEST_EQUAL( {type.get(t, 2)}, 42 );
  TEST_EQUAL( {type.get(t, 3)}, 42 );
  TEST_EQUAL( {type.front(t)}, 42 );
  TEST_EQUAL( {type.back(t)}, 42 );
""")

x.unit(f"{type.data}(): access underlying contiguous array", f"""
  int *data = {type.data(t)};
  data[0] = 100;
  data[1] = 200;
  data[2] = 300;
  data[3] = 400;
  TEST_EQUAL( {type.get(t, 0)}, 100 );
  TEST_EQUAL( {type.get(t, 1)}, 200 );
  TEST_EQUAL( {type.get(t, 2)}, 300 );
  TEST_EQUAL( {type.get(t, 3)}, 400 );
""")

x.unit(f"{type.contains}(): test contains for present and absent elements", f"""
  {type.set(t, 0, 5)};
  {type.set(t, 1, 15)};
  {type.set(t, 2, 25)};
  {type.set(t, 3, 35)};
  TEST_TRUE( {type.contains(t, 5)} );
  TEST_TRUE( {type.contains(t, 15)} );
  TEST_TRUE( {type.contains(t, 25)} );
  TEST_TRUE( {type.contains(t, 35)} );
  TEST_FALSE( {type.contains(t, 45)} );
""")

x.unit(f"{type.range}(): iterate range forward and backward", f"""
  int sum = 0;
  {r.definition};
  {type.set(t, 0, 1)};
  {type.set(t, 1, 2)};
  {type.set(t, 2, 3)};
  {type.set(t, 3, 4)};
  for({r} = {type.range.new(t)}; !{type.range.empty(r)}; {type.range.move_front(r)}) {{
    sum += {type.range.front(r)};
  }}
  TEST_EQUAL( sum, 10 );

  {r} = {type.range.new(t)};
  TEST_EQUAL( {type.range.size(r)}, 4 );
  TEST_EQUAL( {type.range.front(r)}, 1 );
  TEST_EQUAL( *{type.range.front_view(r)}, 1 );
  TEST_EQUAL( {type.range.back(r)}, 4 );
  TEST_EQUAL( *{type.range.back_view(r)}, 4 );
  TEST_EQUAL( {type.range.get(r, 2)}, 3 );
  TEST_EQUAL( *{type.range.view(r, 2)}, 3 );

  {type.range.move_back(r)};
  TEST_EQUAL( {type.range.size(r)}, 3 );
  TEST_EQUAL( {type.range.back(r)}, 3 );

  {type.range.move_front(r)};
  TEST_EQUAL( {type.range.size(r)}, 2 );
  TEST_EQUAL( {type.range.front(r)}, 2 );
""")

x.unit(f"{type.sort}(), {type.sorted}(), {type.reverse}(): sort and reverse array", f"""
  {type.set(t, 0, 40)};
  {type.set(t, 1, 10)};
  {type.set(t, 2, 30)};
  {type.set(t, 3, 20)};
  TEST_FALSE( {type.sorted(t)} );

  {type.sort(t)};
  TEST_TRUE( {type.sorted(t)} );
  TEST_EQUAL( {type.get(t, 0)}, 10 );
  TEST_EQUAL( {type.get(t, 1)}, 20 );
  TEST_EQUAL( {type.get(t, 2)}, 30 );
  TEST_EQUAL( {type.get(t, 3)}, 40 );

  {type.reverse(t)};
  TEST_FALSE( {type.sorted(t)} );
  TEST_EQUAL( {type.get(t, 0)}, 40 );
  TEST_EQUAL( {type.get(t, 1)}, 30 );
  TEST_EQUAL( {type.get(t, 2)}, 20 );
  TEST_EQUAL( {type.get(t, 3)}, 10 );
""")

x.unit(f"{type.binary_search}(), {type.lower_bound}(), {type.upper_bound}(): binary search on sorted array", f"""
  {type.set(t, 0, 10)};
  {type.set(t, 1, 20)};
  {type.set(t, 2, 30)};
  {type.set(t, 3, 40)};

  TEST_TRUE( {type.binary_search(t, 20)} );
  TEST_TRUE( {type.binary_search(t, 10)} );
  TEST_TRUE( {type.binary_search(t, 40)} );
  TEST_FALSE( {type.binary_search(t, 25)} );
  TEST_FALSE( {type.binary_search(t, 5)} );
  TEST_FALSE( {type.binary_search(t, 50)} );

  TEST_EQUAL( {type.lower_bound(t, 20)}, 1 );
  TEST_EQUAL( {type.lower_bound(t, 25)}, 2 );
  TEST_EQUAL( {type.upper_bound(t, 20)}, 2 );
""")


x.setup(f"""
  {t1.definition};
  {type.create(t1)};
  {t2.definition};
  {type.create(t2)};
""")
x.cleanup(f"""
  {type.destroy(t1) if type.destructible else str()}
  {type.destroy(t2) if type.destructible else str()}
""")

x.unit(f"{type.equal}(): compare arrays", f"""
  TEST_TRUE( {type.equal(t1, t2)} );
  {type.set(t1, 0, 7)};
  TEST_FALSE( {type.equal(t1, t2)} );
  {type.set(t2, 0, 7)};
  TEST_TRUE( {type.equal(t1, t2)} );
  {type.set(t1, 3, 8)};
  {type.set(t2, 3, 9)};
  TEST_FALSE( {type.equal(t1, t2)} );
""")

x.unit(f"{type.hash}(): hash equal arrays", f"""
  {type.fill(t1, 42)};
  {type.fill(t2, 42)};
  TEST_EQUAL( {type.hash(t1)}, {type.hash(t2)} );
""")

x.unit(f"{type.copy}(): copy array", f"""
  {type.set(t1, 0, 100)};
  {type.set(t1, 1, 200)};
  {type.set(t1, 2, 300)};
  {type.set(t1, 3, 400)};
  {type.copy(t2, t1)};
  TEST_TRUE( {type.equal(t1, t2)} );
  TEST_EQUAL( {type.get(t2, 0)}, 100 );
  TEST_EQUAL( {type.get(t2, 1)}, 200 );
  TEST_EQUAL( {type.get(t2, 2)}, 300 );
  TEST_EQUAL( {type.get(t2, 3)}, 400 );
""")

x.unit(f"{type.move}(): move array", f"""
  {type.set(t1, 0, 111)};
  {type.set(t1, 1, 222)};
  {type.set(t1, 2, 333)};
  {type.set(t1, 3, 444)};
  {type.move(t2, t1)};
  TEST_EQUAL( {type.get(t2, 0)}, 111 );
  TEST_EQUAL( {type.get(t2, 1)}, 222 );
  TEST_EQUAL( {type.get(t2, 2)}, 333 );
  TEST_EQUAL( {type.get(t2, 3)}, 444 );
""")

x.unit(f"{type.swap}(): swap arrays", f"""
  {type.fill(t1, 10)};
  {type.fill(t2, 20)};
  {type.swap(t1, t2)};
  TEST_EQUAL( {type.get(t1, 0)}, 20 );
  TEST_EQUAL( {type.get(t1, 3)}, 20 );
  TEST_EQUAL( {type.get(t2, 0)}, 10 );
  TEST_EQUAL( {type.get(t2, 3)}, 10 );
""")


from metac.list import List

list_t = List("int_array_list", type)
xl = Type(list_t)
tl = list_t.variable("tl")
arr1 = type.variable("arr1")
arr2 = type.variable("arr2")
arr_out = type.variable("arr_out")

xl.setup(f"""
  {tl.definition};
  {list_t.create(tl)};
  {arr1.definition};
  {type.create(arr1)};
  {type.fill(arr1, 10)};
  {arr2.definition};
  {type.create(arr2)};
  {type.fill(arr2, 20)};
  {arr_out.definition};
  {type.create(arr_out)};
""")
xl.cleanup(f"""
  {f"{list_t.destroy(tl)};" if list_t.destructible else str()}
  {f"{type.destroy(arr1)};" if type.destructible else str()}
  {f"{type.destroy(arr2)};" if type.destructible else str()}
  {f"{type.destroy(arr_out)};" if type.destructible else str()}
""")

xl.unit(f"{list_t}: use Array as element in List", f"""
  {list_t.push_front(tl, arr1)};
  {list_t.push_front(tl, arr2)};
  TEST_EQUAL( {list_t.size(tl)}, 2 );
  {arr_out} = {list_t.front(tl)};
  TEST_EQUAL( {type.get(arr_out, 0)}, 20 );
  TEST_EQUAL( {type.get(arr_out, 3)}, 20 );
  {arr_out} = {list_t.pop_front(tl)};
  TEST_EQUAL( {type.get(arr_out, 0)}, 20 );
  TEST_EQUAL( {list_t.size(tl)}, 1 );
  {arr_out} = {list_t.front(tl)};
  TEST_EQUAL( {type.get(arr_out, 0)}, 10 );
""")

