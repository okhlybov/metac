# Value-type test units: the condensed ports of the hand-crafted metac.test
# modules covering the non-container catalog - strings and string buffers,
# plain and intrusive options, tagged variants, records, the two bit set flavors
# and the emplacement scenarios the container matrix cannot reach. Unlike the
# matrix modules these spell out their units directly against the autotest
# Unit/Type framework (the module is picked up by the walk_packages import).

import metac.std as std
from metac.string import String
from metac.string_buffer import Buffer
from metac.option import Option
from metac.intrusive_option import Option as IntrusiveOption
from metac.variant import Variant
from metac.record import Record
from metac.reference import Counted
from metac.bit_array import Array as BitArray
from metac.bit_vector import Vector as BitVector
from metac.array import Array
from metac.vector import Vector

from metac.autotest import Type
from metac.autotest.elements import KINDS

_cstring = KINDS["cstring"].type
_composite = KINDS["comp"].type


def s(x):
  return f'"{x}"'


# --------------------------------------------------------------------------- #
# String
# --------------------------------------------------------------------------- #

str_t = String("at_string")
x_str = Type(str_t, dependencies=[_cstring] if False else [])

st = str_t.variable("st")
st2 = str_t.variable("st2")
x_str.setup(f"""
  {st.definition};
  {str_t.create(st)};
""")
x_str.cleanup(f"""
  {str_t.destroy(st)};
""")

x_str.unit(f"{str_t.empty}(): freshly created string is empty", f"""
  TEST_TRUE({str_t.empty(st)});
  TEST_EQUAL({str_t.size(st)}, 0);
  TEST_EQUAL_CHARS(st, "");
""")

x_str.unit(f"{str_t.format}(): format simple text", f"""
  int ret = {str_t.format(st, s("Hello, %s!"), s("world"))};
  TEST_EQUAL(ret, 13);
  TEST_EQUAL_CHARS(st, "Hello, world!");
""")

x_str.unit(f"{str_t.format}(): format numbers and multiple specifiers", f"""
  int ret = {str_t.format(st, s("%d-%x-%c"), 42, 255, "'Z'")};
  TEST_EQUAL(ret, 7);
  TEST_EQUAL_CHARS(st, "42-ff-Z");
""")

x_str.unit(f"{str_t.format}(): self-referencing format argument", f"""
  {str_t.format(st, s("hello"))};
  {str_t.format(st, s("[%s]"), st)};
  TEST_EQUAL_CHARS(st, "[hello]");
  TEST_EQUAL({str_t.size(st)}, 7);
""")

x_str.unit(f"{str_t.copy}(): replicate and destroy the copy", f"""
  {str_t.format(st, s("payload"))};
  {st2.definition};
  {str_t.create(st2)};
  {str_t.copy(st2, st)};
  TEST_TRUE({str_t.equal(st2, st)});
  TEST_EQUAL_CHARS(st2, "payload");
  {str_t.destroy(st2)};
""")


# --------------------------------------------------------------------------- #
# StringBuffer - the small scratch capacity forces the scratch boundary
# crossings and the chunked append paths (including the ownership transfers)
# --------------------------------------------------------------------------- #

buf = Buffer("at_string_buffer", scratch_capacity=16, chunk_shift=4)
x_buf = Type(buf, dependencies=[_cstring])

bt = buf.variable("bt")
bt2 = buf.variable("bt2")
x_buf.setup(f"""
  {bt.definition};
  {buf.create(bt)};
""")
x_buf.cleanup(f"""
  {buf.destroy(bt)};
""")

x_buf.unit(f"{buf.empty}(): freshly created buffer", f"""
  TEST_TRUE({buf.empty(bt)});
  TEST_EQUAL({buf.size(bt)}, 0);
  TEST_EQUAL_CHARS({buf.view(bt)}, "");
""")

x_buf.unit(f"{buf.push_char}(): push characters across the scratch capacity", f"""
  size_t i;
  for(i = 0; i < 20; ++i) {buf.push_char(bt, "(char)('a' + i)")};
  TEST_EQUAL({buf.size(bt)}, 20);
  TEST_EQUAL_CHARS({buf.view(bt)}, "abcdefghijklmnopqrst");
""")

x_buf.unit(f"{buf.push}(): push strings within and beyond the scratch", f"""
  {buf.push(bt, s("hello "))};
  {buf.push(bt, s("world!"))};
  TEST_EQUAL({buf.size(bt)}, 12);
  TEST_EQUAL_CHARS({buf.view(bt)}, "hello world!");
  TEST_EQUAL_CHARS({buf.view(bt)}, "hello world!"); /* appending after view keeps contents */
  {buf.push(bt, s(" again"))};
  TEST_EQUAL_CHARS({buf.view(bt)}, "hello world! again");
""")

x_buf.unit(f"{buf.push_slice}(): push substring slices", f"""
  {buf.push(bt, s("0123456789ABCDEFGHIJ"))};
  TEST_EQUAL({buf.size(bt)}, 20);
  TEST_EQUAL_CHARS({buf.view(bt)}, "0123456789ABCDEFGHIJ");
""")

x_buf.unit(f"{buf.push_int}(): push numeric integer types", f"""
  {buf.push_int(bt, -42)};
  {buf.push_char(bt, "','")};
  {buf.push_uint(bt, 42)};
  {buf.push_char(bt, "','")};
  {buf.push_long(bt, '-100000L')};
  {buf.push_char(bt, "','")};
  {buf.push_ulong(bt, '100000UL')};
  TEST_EQUAL_CHARS({buf.view(bt)}, "-42,42,-100000,100000");
""")

x_buf.unit(f"{buf.push_format}(): push formatted string", f"""
  int ret = {buf.push_format(bt, s("%s=%d"), s("answer"), 42)};
  TEST_TRUE(ret >= 0);
  TEST_EQUAL_CHARS({buf.view(bt)}, "answer=42");
""")

x_buf.unit(f"{buf.copy}(): copy buffer with dirty scratch and chunks", f"""
  {bt2.definition};
  {buf.create(bt2)};
  {buf.push(bt, s("very_long_string_that_exceeds_scratch_capacity_and_creates_chunks"))};
  {buf.push_char(bt, "'!'")};
  {buf.copy(bt2, bt)};
  TEST_EQUAL({buf.size(bt2)}, {buf.size(bt)});
  TEST_EQUAL_CHARS({buf.view(bt2)}, "very_long_string_that_exceeds_scratch_capacity_and_creates_chunks!");
  {buf.destroy(bt2)};
""")

x_buf.unit(f"{buf.take}(): extract the owned string and reset the buffer", f"""
  char* taken;
  {buf.push(bt, s("take_me"))};
  taken = {buf.take(bt)};
  TEST_NOT_NULL(taken);
  TEST_EQUAL_CHARS(taken, "take_me");
  {_cstring.destroy("taken")};
  TEST_TRUE({buf.empty(bt)});
  TEST_EQUAL({buf.size(bt)}, 0);
""")

x_buf.unit(f"{buf.clear}(): clear and reuse", f"""
  {buf.push(bt, s("scratch me"))};
  {buf.clear(bt)};
  TEST_TRUE({buf.empty(bt)});
  {buf.push(bt, s("reused"))};
  TEST_EQUAL_CHARS({buf.view(bt)}, "reused");
""")

x_buf.unit(f"{buf.move}(): transfer ownership leaving the source empty", f"""
  {bt2.definition};
  {buf.create(bt2)};
  {buf.push(bt, s("moving"))};
  {buf.move(bt2, bt)};
  TEST_TRUE({buf.empty(bt)});
  TEST_EQUAL_CHARS({buf.view(bt2)}, "moving");
  {buf.destroy(bt2)};
""")


# --------------------------------------------------------------------------- #
# Plain Option over int, with and without user states
# --------------------------------------------------------------------------- #

opt = Option("at_int_option", "int")
x_opt = Type(opt)

ot = opt.variable("ot")
ot2 = opt.variable("ot2")
_ot2_destroy = f"{_ot2_destroy}" if opt.destructible else ""
x_opt.setup(f"""
  {ot.definition};
  {opt.create(ot)};
""")
x_opt.cleanup(f"""
  {opt.destroy(ot) if opt.destructible else ""};
""")

x_opt.unit(f"{opt.create}(): fresh option is empty", f"""
  TEST_TRUE({opt.empty(ot)});
  TEST_FALSE({opt.primed(ot)});
  TEST_EQUAL({opt.state(ot)}, 0);
""")

x_opt.unit(f"{opt.set}(): engage with a value", f"""
  {opt.set(ot, 42)};
  TEST_TRUE({opt.primed(ot)});
  TEST_FALSE({opt.empty(ot)});
  TEST_EQUAL({opt.value(ot)}, 42);
  TEST_EQUAL({opt.state(ot)}, -1);
""")

x_opt.unit(f"{opt.set}(): overwrite the engaged value", f"""
  {opt.set(ot, 7)};
  {opt.set(ot, 9)};
  TEST_EQUAL({opt.value(ot)}, 9);
""")

x_opt.unit(f"{opt.value_view}(): borrow the engaged value", f"""
  {opt.set(ot, 7)};
  TEST_EQUAL(*{opt.value_view(ot)}, 7);
""")

x_opt.unit(f"{opt.reset}(): release back to empty", f"""
  {opt.set(ot, 42)};
  {opt.reset(ot)};
  TEST_TRUE({opt.empty(ot)});
  TEST_EQUAL({opt.state(ot)}, 0);
""")

x_opt.unit(f"{opt.emplace}(): construct in place", f"""
  {opt.emplace(ot)};
  TEST_TRUE({opt.primed(ot)});
  TEST_EQUAL({opt.value(ot)}, 0);
""")

x_opt.unit(f"{opt.equal}(): empty, engaged and mixed", f"""
  {ot2.definition};
  {opt.create(ot2)};
  TEST_TRUE({opt.equal(ot, ot2)});
  {opt.set(ot, 1)};
  TEST_FALSE({opt.equal(ot, ot2)});
  {opt.set(ot2, 1)};
  TEST_TRUE({opt.equal(ot, ot2)});
  {opt.set(ot2, 2)};
  TEST_FALSE({opt.equal(ot, ot2)});
  {_ot2_destroy}
""")

x_opt.unit(f"{opt.copy}(): replicate value and state", f"""
  {ot2.definition};
  {opt.create(ot2)};
  {opt.set(ot, 33)};
  {opt.copy(ot2, ot)};
  TEST_TRUE({opt.primed(ot2)});
  TEST_EQUAL({opt.value(ot2)}, 33);
  {opt.reset(ot)};
  {opt.copy(ot2, ot)};
  TEST_TRUE({opt.empty(ot2)});
  {_ot2_destroy}
""")

x_opt.unit(f"{opt.move}(): transfer leaving the source empty", f"""
  {ot2.definition};
  {opt.create(ot2)};
  {opt.set(ot, 11)};
  {opt.move(ot2, ot)};
  TEST_TRUE({opt.empty(ot)});
  TEST_EQUAL({opt.value(ot2)}, 11);
  {_ot2_destroy}
""")

x_opt.unit(f"{opt.swap}(): exchange keeps both sides valid", f"""
  {ot2.definition};
  {opt.create(ot2)};
  {opt.set(ot, 1)};
  {opt.set(ot2, 2)};
  {opt.swap(ot, ot2)};
  TEST_EQUAL({opt.value(ot)}, 2);
  TEST_EQUAL({opt.value(ot2)}, 1);
  {_ot2_destroy}
""")

x_opt.unit(f"{opt.hash}(): equal options hash equally", f"""
  {ot2.definition};
  {opt.create(ot2)};
  {opt.set(ot, 5)};
  {opt.set(ot2, 5)};
  TEST_EQUAL({opt.hash(ot)}, {opt.hash(ot2)});
  {_ot2_destroy}
""")

x_opt.unit(f"{opt.compare}(): empty orders before the engaged value", f"""
  {ot2.definition};
  {opt.create(ot2)};
  {opt.set(ot, 1)};
  TEST_TRUE({opt.compare(ot2, ot)} < 0);
  TEST_TRUE({opt.compare(ot, ot2)} > 0);
  TEST_EQUAL({opt.compare(ot, ot)}, 0);
  {_ot2_destroy}
""")


state_opt = Option("at_int_state_option", "int", states=3)
x_state = Type(state_opt)
stt = state_opt.variable("stt")
x_state.setup(f"""
  {stt.definition};
  {state_opt.create(stt)};
""")
x_state.cleanup("")

x_state.unit(f"{state_opt.set_state}(): reach the user states and back", f"""
  {state_opt.set(stt, 42)};
  {state_opt.set_state(stt, 1)};
  TEST_FALSE({state_opt.empty(stt)});
  TEST_FALSE({state_opt.primed(stt)});
  TEST_EQUAL({state_opt.state(stt)}, 1);
  {state_opt.set_state(stt, 2)};
  TEST_EQUAL({state_opt.state(stt)}, 2);
  {state_opt.set_state(stt, 0)};
  TEST_TRUE({state_opt.empty(stt)});
""")

x_state.unit(f"{state_opt.reset}(): release from a user state", f"""
  {state_opt.set_state(stt, 2)};
  {state_opt.reset(stt)};
  TEST_TRUE({state_opt.empty(stt)});
""")


# --------------------------------------------------------------------------- #
# IntrusiveOption - the states encoded as sentinel element values
# --------------------------------------------------------------------------- #

_int_states = {
  "empty": (lambda e: f"{e} == INT_MIN", lambda e: f"{e} = INT_MIN"),
  "na": (lambda e: f"{e} == INT_MAX", lambda e: f"{e} = INT_MAX"),
}

iopt = IntrusiveOption("at_int_intrusive_option", "int", _int_states, dependencies=(std.limits_h,))
x_iopt = Type(iopt)

it = iopt.variable("it")
it2 = iopt.variable("it2")
x_iopt.setup(f"""
  {it.definition};
  {iopt.create(it)};
""")
x_iopt.cleanup("")

x_iopt.unit(f"{iopt.create}(): fresh state is the empty sentinel", f"""
  TEST_EQUAL(it, INT_MIN);
  TEST_TRUE({iopt.empty(it)});
  TEST_FALSE({iopt.primed(it)});
  TEST_EQUAL({iopt.state(it)}, 0);
""")

x_iopt.unit(f"{iopt.set}(): engage with a value", f"""
  {iopt.set(it, 42)};
  TEST_TRUE({iopt.primed(it)});
  TEST_EQUAL({iopt.value(it)}, 42);
  TEST_EQUAL({iopt.state(it)}, -1);
""")

x_iopt.unit(f"{iopt.reset}(): release back to the sentinel", f"""
  {iopt.set(it, 42)};
  {iopt.reset(it)};
  TEST_EQUAL(it, INT_MIN);
  TEST_TRUE({iopt.empty(it)});
""")

x_iopt.unit(f"{iopt.set_state}(): reach the user sentinel state", f"""
  {iopt.set(it, 1)};
  {iopt.set_state(it, 1)};
  TEST_EQUAL(it, INT_MAX);
  TEST_TRUE({iopt.na(it)});
  TEST_FALSE({iopt.primed(it)});
  TEST_EQUAL({iopt.state(it)}, 1);
""")

x_iopt.unit(f"{iopt.copy}(): replicate the value and the state", f"""
  {it2.definition};
  {iopt.create(it2)};
  {iopt.set(it2, 7)};
  {iopt.copy(it, it2)};
  TEST_TRUE({iopt.primed(it)});
  TEST_EQUAL({iopt.value(it)}, 7);
  {iopt.reset(it2)};
  {iopt.set_state(it2, 1)};
  {iopt.copy(it, it2)};
  TEST_EQUAL(it, INT_MAX);
  TEST_TRUE({iopt.na(it)});
""")

x_iopt.unit(f"{iopt.move}(): transfer leaving the sentinel source", f"""
  {it2.definition};
  {iopt.create(it2)};
  {iopt.set(it2, 9)};
  {iopt.move(it, it2)};
  TEST_EQUAL(it2, INT_MIN);
  TEST_EQUAL({iopt.value(it)}, 9);
""")

x_iopt.unit(f"{iopt.equal}(): sentinels, values and user states", f"""
  {it2.definition};
  {iopt.create(it2)};
  TEST_TRUE({iopt.equal(it, it2)});
  {iopt.set(it, 1)};
  TEST_FALSE({iopt.equal(it, it2)});
  {iopt.set(it2, 1)};
  TEST_TRUE({iopt.equal(it, it2)});
  {iopt.set_state(it2, 1)};
  TEST_FALSE({iopt.equal(it, it2)});
""")

x_iopt.unit(f"{iopt.compare}(): empty < value < user state", f"""
  {it2.definition};
  {iopt.create(it2)};
  {iopt.set(it, 1)};
  TEST_TRUE({iopt.compare(it2, it)} < 0);
  {iopt.set_state(it2, 1)};
  TEST_TRUE({iopt.compare(it2, it)} > 0);
""")


_cstr_states = {
  "empty": (lambda e: f"{e} == NULL", lambda e: f"{e} = NULL"),
}

copt = IntrusiveOption("at_cstring_intrusive_option", _cstring, _cstr_states)
x_copt = Type(copt, dependencies=[_cstring])

ct = copt.variable("ct")
x_copt.setup(f"""
  {ct.definition};
  {copt.create(ct)};
""")
x_copt.cleanup(f"""
  {copt.destroy(ct)};
""")

x_copt.unit(f"{copt.create}(): empty state is the NULL sentinel", f"""
  TEST_NULL(ct);
  TEST_TRUE({copt.empty(ct)});
""")

x_copt.unit(f"{copt.set}(): engage with an owning value", f"""
  {copt.set(ct, s("hello"))};
  TEST_TRUE({copt.primed(ct)});
  {{ char* v = {copt.value(ct)}; TEST_EQUAL_CHARS(v, "hello"); {_cstring.destroy("v")}; }}
""")

x_copt.unit(f"{copt.set}(): overwrite releases the previous value", f"""
  {copt.set(ct, s("one"))};
  {copt.set(ct, s("two"))};
  {{ char* v = {copt.value(ct)}; TEST_EQUAL_CHARS(v, "two"); {_cstring.destroy("v")}; }}
""")

x_copt.unit(f"{copt.reset}(): release the value back to NULL", f"""
  {copt.set(ct, s("bye"))};
  {copt.reset(ct)};
  TEST_NULL(ct);
  TEST_TRUE({copt.empty(ct)});
""")


# --------------------------------------------------------------------------- #
# Variant with a primitive and a reference-counted composite alternative
# --------------------------------------------------------------------------- #

_comp_arc = Counted(_composite, name="at_composite_counted")
var = Variant("at_content_variant", {"amount": "int", "composite": _comp_arc})
x_var = Type(var, dependencies=[_composite])

vt = var.variable("vt")
vt2 = var.variable("vt2")
pv = _comp_arc.variable("p")
x_var.setup(f"""
  {vt.definition};
  {var.create(vt)};
""")
x_var.cleanup(f"""
  {var.destroy(vt)};
""")

x_var.unit(f"{var.create}(): create in the empty state", f"""
  TEST_TRUE({var.is_empty(vt)});
  TEST_FALSE({var.is_amount(vt)});
  TEST_FALSE({var.is_composite(vt)});
""")

x_var.unit(f"{var.set_amount}(): hold a primitive alternative", f"""
  {var.set_amount(vt, 42)};
  TEST_TRUE({var.is_amount(vt)});
  TEST_EQUAL({var.get_amount(vt)}, 42);
""")

x_var.unit(f"{var.set_composite}(): hold the shared composite", f"""
  {pv.definition};
  {_comp_arc.create(pv, 7)};
  {var.set_composite(vt, pv)};
  TEST_TRUE({var.is_composite(vt)});
  TEST_EQUAL(*{var.get_composite_view(vt)}->value, 7);
  {_comp_arc.destroy(pv)}; /* the variant keeps the instance alive */
  TEST_EQUAL(*{var.get_composite_view(vt)}->value, 7);
""")

x_var.unit(f"{var.set_amount}(): switching away releases the composite", f"""
  {pv.definition};
  {_comp_arc.create(pv, 7)};
  {var.set_composite(vt, pv)};
  {var.set_amount(vt, 1)};
  TEST_TRUE({var.is_amount(vt)});
  TEST_TRUE({var.is_empty(vt)} == 0);
  {_comp_arc.destroy(pv)};
""")

x_var.unit(f"{var.set_composite}(): re-set the same alternative", f"""
  {pv.definition};
  {_comp_arc.create(pv, 7)};
  {var.set_composite(vt, pv)};
  {var.set_composite(vt, pv)};
  TEST_TRUE({var.is_composite(vt)});
  TEST_EQUAL(*{var.get_composite_view(vt)}->value, 7);
  {_comp_arc.destroy(pv)};
""")

_var_self_view = var.get_composite_view(vt)
x_var.unit(f"{var.set_composite}(): self-assignment through the own view is a no-op", f"""
  {pv.definition};
  {_comp_arc.create(pv, 7)};
  {var.set_composite(vt, pv)};
  {var.set_composite(vt, _var_self_view)};
  TEST_TRUE({var.is_composite(vt)});
  TEST_EQUAL(*{var.get_composite_view(vt)}->value, 7);
  {_comp_arc.destroy(pv)};
""")

x_var.unit(f"{var.emplace_amount}(): construct the alternative in place", f"""
  {var.emplace_amount(vt)};
  TEST_TRUE({var.is_amount(vt)});
  TEST_EQUAL({var.get_amount(vt)}, 0);
""")

x_var.unit(f"{var.copy}(): replicate the shared composite", f"""
  {pv.definition};
  {vt2.definition};
  {var.create(vt2)};
  {_comp_arc.create(pv, 13)};
  {var.set_composite(vt, pv)};
  {var.copy(vt2, vt)};
  TEST_TRUE({var.is_composite(vt2)});
  TEST_EQUAL(*{var.get_composite_view(vt2)}->value, 13);
  {_comp_arc.destroy(pv)};
  {var.destroy(vt2)};
""")

x_var.unit(f"{var.move}(): transfer leaving the source empty", f"""
  {vt2.definition};
  {var.create(vt2)};
  {var.set_amount(vt, 3)};
  {var.move(vt2, vt)};
  TEST_TRUE({var.is_empty(vt)});
  TEST_TRUE({var.is_amount(vt2)});
  TEST_EQUAL({var.get_amount(vt2)}, 3);
  {var.destroy(vt2)};
""")


# --------------------------------------------------------------------------- #
# Record with a primitive and an owning string field
# --------------------------------------------------------------------------- #

rec = Record("at_value_record", {"tag": "int", "text": _cstring})
x_rec = Type(rec, dependencies=[_cstring])

rt = rec.variable("rt")
rt2 = rec.variable("rt2")
x_rec.setup(f"""
  {rt.definition};
  {rec.create(rt)};
""")
x_rec.cleanup(f"""
  {rec.destroy(rt)};
""")

x_rec.unit(f"{rec.set_tag}(): set and read the fields", f"""
  {rec.set_tag(rt, 7)};
  {rec.set_text(rt, s("seven"))};
  TEST_EQUAL({rec.get_tag(rt)}, 7);
  TEST_EQUAL_CHARS({rec.get_text_view(rt)}, "seven");
""")

_rec_self_view = rec.get_text_view(rt)
x_rec.unit(f"{rec.set_text}(): self-assignment through the own view is a no-op", f"""
  {rec.set_text(rt, s("keep me"))};
  {rec.set_text(rt, _rec_self_view)};
  TEST_EQUAL_CHARS({rec.get_text_view(rt)}, "keep me");
""")

x_rec.unit(f"{rec.emplace_text}(): default-construct the field in place", f"""
  {rec.set_tag(rt, 1)};
  {rec.set_text(rt, s("replace me"))};
  {rec.emplace_tag(rt)};
  {rec.emplace_text(rt)};
  TEST_EQUAL({rec.get_tag(rt)}, 0);
  TEST_EQUAL_CHARS({rec.get_text_view(rt)}, "");
""")

x_rec.unit(f"{rec.copy}(): member-wise replicate", f"""
  {rt2.definition};
  {rec.create(rt2)};
  {rec.set_tag(rt, 9)};
  {rec.set_text(rt, s("nine"))};
  {rec.copy(rt2, rt)};
  TEST_EQUAL({rec.get_tag(rt2)}, 9);
  TEST_EQUAL_CHARS({rec.get_text_view(rt2)}, "nine");
  {rec.destroy(rt2)};
""")

x_rec.unit(f"{rec.move}(): transfer leaving the source valid", f"""
  {rt2.definition};
  {rec.create(rt2)};
  {rec.set_tag(rt, 4)};
  {rec.set_text(rt, s("four"))};
  {rec.move(rt2, rt)};
  TEST_EQUAL({rec.get_tag(rt2)}, 4);
  TEST_EQUAL_CHARS({rec.get_text_view(rt2)}, "four");
  {rec.destroy(rt2)};
""")


# --------------------------------------------------------------------------- #
# Bit sets - fixed capacity array and dynamic vector flavors
# --------------------------------------------------------------------------- #

bits = BitArray("at_bitarray", 20)
x_bits = Type(bits)

gt = bits.variable("gt")
gt2 = bits.variable("gt2")
x_bits.setup(f"""
  {gt.definition};
  {bits.create(gt)};
""")
x_bits.cleanup("")

x_bits.unit(f"{bits.none}(): fresh bit array holds no bits", f"""
  TEST_TRUE({bits.none(gt)});
  TEST_FALSE({bits.any(gt)});
  TEST_EQUAL({bits.count(gt)}, 0);
  TEST_EQUAL({bits.capacity(gt)}, 20);
""")

x_bits.unit(f"{bits.set}(): set, test and count", f"""
  {bits.set(gt, 0)};
  {bits.set(gt, 7)};
  {bits.set(gt, 19)};
  TEST_TRUE({bits.test(gt, 7)});
  TEST_FALSE({bits.test(gt, 6)});
  TEST_EQUAL({bits.count(gt)}, 3);
""")

x_bits.unit(f"{bits.clear}(): clear a set bit", f"""
  {bits.set(gt, 5)};
  {bits.clear(gt, 5)};
  TEST_FALSE({bits.test(gt, 5)});
""")

x_bits.unit(f"{bits.flip}(): flip a bit twice", f"""
  {bits.flip(gt, 3)};
  TEST_TRUE({bits.test(gt, 3)});
  {bits.flip(gt, 3)};
  TEST_FALSE({bits.test(gt, 3)});
""")

x_bits.unit(f"{bits.set_all}(): set every bit", f"""
  {bits.set_all(gt)};
  TEST_EQUAL({bits.count(gt)}, 20);
""")

x_bits.unit(f"{bits.flip_all}(): full flip and back", f"""
  {bits.flip_all(gt)};
  TEST_EQUAL({bits.count(gt)}, 20);
  {bits.flip_all(gt)};
  TEST_EQUAL({bits.count(gt)}, 0);
""")

x_bits.unit(f"{bits.flip_all}(): flip a partial state", f"""
  {bits.set(gt, 0)};
  {bits.set(gt, 1)};
  {bits.set(gt, 2)};
  {bits.flip_all(gt)};
  TEST_EQUAL({bits.count(gt)}, 17);
""")

x_bits.unit(f"{bits.find_first}(): none, found and advanced", f"""
  TEST_EQUAL({bits.find_first(gt)}, 20);
  {bits.set(gt, 5)};
  TEST_EQUAL({bits.find_first(gt)}, 5);
  {bits.clear(gt, 5)};
  {bits.set(gt, 12)};
  TEST_EQUAL({bits.find_first(gt)}, 12);
""")

x_bits.unit(f"{bits.copy}(): replicate and compare", f"""
  {gt2.definition};
  {bits.create(gt2)};
  {bits.set(gt, 1)};
  {bits.set(gt, 4)};
  {bits.copy(gt2, gt)};
  TEST_TRUE({bits.equal(gt, gt2)});
  TEST_EQUAL({bits.hash(gt)}, {bits.hash(gt2)});
  {bits.set(gt2, 9)};
  TEST_FALSE({bits.equal(gt, gt2)});
""")

x_bits.unit(f"{bits.apply_union}(): algebra over partial operands", f"""
  {gt2.definition};
  {bits.create(gt2)};
  {bits.set(gt, 0)};
  {bits.set(gt2, 1)};
  {bits.apply_union(gt, gt2)};
  TEST_EQUAL({bits.count(gt)}, 2);
  {bits.apply_intersection(gt, gt2)};
  TEST_EQUAL({bits.count(gt)}, 1);
  {bits.apply_difference(gt, gt2)};
  TEST_EQUAL({bits.count(gt)}, 0);
  {bits.set(gt, 0)};
  {bits.apply_symmetric_difference(gt, gt2)};
  TEST_EQUAL({bits.count(gt)}, 2);
""")

x_bits.unit(f"{bits.is_subset}(): subset relation", f"""
  {gt2.definition};
  {bits.create(gt2)};
  {bits.set(gt, 0)};
  {bits.set(gt2, 0)};
  {bits.set(gt2, 1)};
  TEST_TRUE({bits.is_subset(gt, gt2)});
  {bits.set(gt, 5)};
  TEST_FALSE({bits.is_subset(gt, gt2)});
""")


bvec = BitVector("at_bitvector")
x_bvec = Type(bvec)

bvt = bvec.variable("bvt")
bvt2 = bvec.variable("bvt2")
x_bvec.setup(f"""
  {bvt.definition};
  {bvec.create(bvt)};
""")
x_bvec.cleanup(f"""
  {bvec.destroy(bvt)};
""")

x_bvec.unit(f"{bvec.empty}(): fresh bit vector is empty", f"""
  TEST_TRUE({bvec.empty(bvt)});
  TEST_EQUAL({bvec.size(bvt)}, 0);
  TEST_TRUE({bvec.none(bvt)});
""")

x_bvec.unit(f"{bvec.push}(): append and pop bits", f"""
  {bvec.push(bvt, 1)};
  {bvec.push(bvt, 0)};
  {bvec.push(bvt, 1)};
  TEST_EQUAL({bvec.count(bvt)}, 2);
  TEST_EQUAL({bvec.pop(bvt)}, 1);
  TEST_EQUAL({bvec.pop(bvt)}, 0);
  TEST_EQUAL({bvec.pop(bvt)}, 1);
  TEST_TRUE({bvec.empty(bvt)});
""")

x_bvec.unit(f"{bvec.reserve}(): preallocate and compact", f"""
  {bvec.reserve(bvt, 200)};
  TEST_TRUE({bvec.capacity(bvt)} >= 200);
  {bvec.compact(bvt)};
  TEST_TRUE({bvec.capacity(bvt)} < 200);
""")

x_bvec.unit(f"{bvec.set}(): word boundary crossing indices", f"""
  {bvec.resize(bvt, 70)};
  {bvec.set(bvt, 63, 1)};
  {bvec.set(bvt, 64, 1)};
  TEST_EQUAL({bvec.get(bvt, 63)}, 1);
  TEST_EQUAL({bvec.get(bvt, 64)}, 1);
  {bvec.clear_bit(bvt, 63)};
  TEST_EQUAL({bvec.get(bvt, 63)}, 0);
  {bvec.flip_bit(bvt, 64)};
  TEST_EQUAL({bvec.get(bvt, 64)}, 0);
""")

x_bvec.unit(f"{bvec.set_all}(): bulk set, reset and flip", f"""
  {bvec.resize(bvt, 100)};
  {bvec.set_all(bvt)};
  TEST_EQUAL({bvec.count(bvt)}, 100);
  TEST_TRUE({bvec.all(bvt)});
  {bvec.reset_all(bvt)};
  TEST_EQUAL({bvec.count(bvt)}, 0);
  {bvec.flip(bvt)};
  TEST_EQUAL({bvec.count(bvt)}, 100);
""")

x_bvec.unit(f"{bvec.find_first}(): none, found and advanced", f"""
  {bvec.resize(bvt, 80)};
  TEST_EQUAL({bvec.find_first(bvt)}, 80);
  {bvec.set(bvt, 65, 1)};
  TEST_EQUAL({bvec.find_first(bvt)}, 65);
  {bvec.clear_bit(bvt, 65)};
  {bvec.set(bvt, 10, 1)};
  TEST_EQUAL({bvec.find_first(bvt)}, 10);
""")

x_bvec.unit(f"{bvec.copy}(): replicate the value", f"""
  {bvec.resize(bvt, 8)};
  {bvec.set(bvt, 1, 1)};
  {bvt2.definition};
  {bvec.create(bvt2)};
  {bvec.copy(bvt2, bvt)};
  TEST_TRUE({bvec.equal(bvt, bvt2)});
  TEST_EQUAL({bvec.size(bvt2)}, 8);
  {bvec.destroy(bvt2)};
""")

x_bvec.unit(f"{bvec.move}(): transfer leaving the source empty", f"""
  {bvec.push(bvt, 1)};
  {bvt2.definition};
  {bvec.create(bvt2)};
  {bvec.move(bvt2, bvt)};
  TEST_TRUE({bvec.empty(bvt)});
  TEST_EQUAL({bvec.size(bvt2)}, 1);
  {bvec.destroy(bvt2)};
""")

x_bvec.unit(f"{bvec.apply_union}(): algebra with mismatched sizes", f"""
  {bvt2.definition};
  {bvec.create(bvt2)};
  {bvec.resize(bvt, 8)};
  {bvec.resize(bvt2, 16)};
  {bvec.set(bvt, 1, 1)};
  {bvec.set(bvt2, 1, 1)};
  {bvec.set(bvt2, 15, 1)};
  {bvec.apply_union(bvt, bvt2)};
  TEST_EQUAL({bvec.size(bvt)}, 16);
  TEST_EQUAL({bvec.count(bvt)}, 2);
  TEST_EQUAL({bvec.count(bvt2)}, 2); /* the source stays unmodified */
  {bvec.destroy(bvt2)};
""")


# --------------------------------------------------------------------------- #
# Emplacement scenarios the container matrix cannot reach
# --------------------------------------------------------------------------- #

sarr = Array("at_emplace_str_array", _cstring, 4)
x_sarr = Type(sarr, dependencies=[_cstring])

sat = sarr.variable("sat")
x_sarr.setup(f"""
  {sat.definition};
  {sarr.create(sat)};
""")
x_sarr.cleanup(f"""
  {sarr.destroy(sat)};
""")

x_sarr.unit(f"{sarr.emplace}(): emplace destroys the previous element in place", f"""
  {sarr.set(sat, 1, s("hello"))};
  TEST_EQUAL_CHARS({sarr.view(sat, 1)}, "hello");
  {sarr.emplace(sat, 1)};
  TEST_EQUAL_CHARS({sarr.view(sat, 1)}, "");
""")


cvec = Vector("at_composite_vector", _composite)
x_cvec = Type(cvec, dependencies=[_composite])

cvt = cvec.variable("cvt")
x_cvec.setup(f"""
  {cvt.definition};
  {cvec.create(cvt)};
""")
x_cvec.cleanup(f"""
  {cvec.destroy(cvt)};
""")

x_cvec.unit(f"{cvec.emplace_back}(): forward construction and destroy the returned copies", f"""
  {cvec.emplace_back(cvt, 42)};
  {cvec.emplace_back(cvt, 99)};
  TEST_EQUAL({cvec.size(cvt)}, 2);
  {{ {_composite} g = {cvec.get(cvt, 0)}; TEST_EQUAL(*g.value, 42); {_composite.destroy("&g")}; }}
  {{ {_composite} g = {cvec.get(cvt, 1)}; TEST_EQUAL(*g.value, 99); {_composite.destroy("&g")}; }}
""")
