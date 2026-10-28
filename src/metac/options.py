import metac.std as std
from metac.hash import XorRot
from metac.core import inout, _type
from metac.core import Composite


#
# Common base of the optional types.
#
# An optional value is a small state machine over the element storage: state 0 is the
# empty state (the technically specified one), state -1 is the engaged state holding the
# element value and states 1 and beyond are of pure user-defined meaning (value-less,
# like the empty state itself). The base is parameterized by a state codec - a set of
# per-state test/mark emitters over the storage expression - and derives the whole
# value protocol plus the optional-specific operations from it.
#
# The plain Optional supplies a codec over an internally stored integer tag while the
# IntrusiveOptional takes user-supplied codecs encoding the states as sentinel element
# values, exactly like the intrusive hash containers encode their slot states.
class Option(Composite):

  brief = "Optional value holding either an element or one of the named states"

  def __init__(self, name, element, *args, hasher=XorRot(), dependencies=(), **kwargs):
    super().__init__(name, *args, dependencies=(*dependencies, std.assert_h, hasher), **kwargs)
    self.element = _type(element)
    self.hasher = hasher
    self.dependencies.add(self.element)

  @property
  def sentinel_states(self):
    return list(range(self.nstates))

  @property
  def engaged_state(self):
    return -1

  def _state_name(self, s):
    return "empty" if s == 0 else None

  # The engaged test is the absence of every value-less state
  def _engaged(self, e):
    tests = [self._is(s)(e) for s in self.sentinel_states]
    return "!(" + " || ".join(f"({t})" for t in tests) + ")"

  def __setup__(self):
    super().__setup__()
    element = self.element
    e = "(*target)"

    with self.create as m:
      m.inline_code = f"""
        assert(target);
        {self._mark(0)(e)};
      """

    destroy_slot = element.destroy(self._slot_var(e)) if self.destructible else ""
    if self.destructible:
      with self.destroy as m:
        m.inline_code = f"""
          assert(target);
          if({self._engaged(e)}) {{{destroy_slot};}}
        """

    with self.copy as m:
      m.inline_code = f"""
        assert(target);
        assert(source);
        if({self._engaged("(*source)")}) {{
          {element.copy(self._slot_var(e), self._slot_var("(*source)"))};
        }}
        {self._mark_states_from(e, "(*source)")};
      """

    with self.move as m:
      m.inline_code = f"""
        assert(target);
        assert(source);
        if({self._engaged("(*source)")}) {{
          {element.move(self._slot_var(e), self._slot_var("(*source)"))};
        }}
        {self._mark_states_from(e, "(*source)")};
        {self._mark(0)("(*source)")};
      """

    # The exchange of the raw representations is the O(1) swap - the total ownership
    # is preserved with each side ending up owning exactly what the other held, so
    # no element protocol needs running at all. The move-through-temp variant this
    # replaces left the temp marked empty while its moved-from slot could hold the
    # default-constructed (allocating) element - leaked by the skipped destroy
    with self.swap as m:
      temp = self.variable("temp")
      m.inline_code = f"""
        {temp.definition};
        assert(left);
        assert(right);
        temp = *{m.left};
        *{m.left} = *{m.right};
        *{m.right} = temp;
      """

    if element.comparable:
      with self.equal as m:
        state_diff = [f"if(({self._is(s)('(*left)')}) != ({self._is(s)('(*right)')})) return 0;" for s in self.sentinel_states]
        m.inline_code = [f"assert(left);", f"assert(right);", *state_diff,
                         f"if(!{self._engaged('(*left)')}) return 1;",
                         f"return {element.equal(self._slot_var('(*left)'), self._slot_var('(*right)'))};"]

    if element.orderable:
      with self.compare as m:
        # empty orders before the value which orders before the user states in index order
        user_states = [s for s in self.sentinel_states if s != 0]
        def side(e):
          chain = [f"({self._is(0)(e)}) ? 0 : "]
          for rank, s in enumerate(user_states, start=2):
            chain.append(f"({self._is(s)(e)}) ? {rank} : ")
          return f"({''.join(chain)}1)"
        m.inline_code = [f"assert(left);", f"assert(right);",
                         f"int l = {side('(*left)')}, r = {side('(*right)')};",
                         f"if(l != r) return l < r ? -1 : +1;",
                         f"if(l != 1) return 0;",
                         f"return {element.compare(self._slot_var('(*left)'), self._slot_var('(*right)'))};"]

    if element.hashable:
      with self.hash as m:
        state = self.hasher.state_t.variable("state")
        m.inline_code = [f"{state.definition}; size_t result;",
                         f"assert(target);",
                         f"{self.hasher.create(state)};",
                         f"{self.hasher.update(state, f'(size_t)({self._state_chain(e)})')};",
                         f"if({self._engaged(e)}) {self.hasher.update(state, element.hash(self._slot_var(e)))};",
                         f"result = {self.hasher.hash(state)};",
                         f"{self.hasher.destroy(state)};",
                         f"return result;"]

    with self.method("int", "empty", {"target": self}, brief="Check for the empty state",
      description="""
        Reports whether the optional holds neither a value nor a user state - the
        technically specified empty state.

        @param[in] target the optional to check
        @return non-zero when the optional is in the empty state
      """) as m:
      m.inline_code = f"""
        assert(target);
        return {self._is(0)(e)};
      """

    for s in self.sentinel_states:
      if s != 0:
        name = self._state_name(s)
        if name and name != "empty":
          with self.method("int", name, {"target": self}, brief=f"Check for the {name} state",
            description=f"""
              Reports whether the optional is in the {name} state.

              @param[in] target the optional to check
              @return non-zero when the optional is in the {name} state
            """) as m:
            m.inline_code = f"""
              assert(target);
              return {self._is(s)(e)};
            """

    with self.method("int", "primed", {"target": self}, brief="Check for the engaged state",
      description="""
        Reports whether the optional currently holds an element value. An optional in
        one of the user states holds no value either yet is not empty.

        @param[in] target the optional to check
        @return non-zero when the optional holds an element value
      """) as m:
      m.inline_code = f"""
        assert(target);
        return {self._engaged(e)};
      """

    with self.method("int", "state", {"target": self}, brief="Get the current state",
      description="""
        Returns the current state: 0 for the empty state, -1 for the engaged state
        holding the value and the user-defined indices (1+) beyond that.

        @param[in] target the optional to inspect
        @return the current state index
      """) as m:
      m.inline_code = f"""
        assert(target);
        return {self._state_chain(e)};
      """

    if element.copyable:
      with self.method(element, "value", {"target": self}, constraint=lambda: element.copyable, brief="Get the held value",
        description="""
          Returns a copy of the held element value. The optional must hold a value.

          @param[in] target the optional to read
          @return the held element value
        """) as m:
        result = m.result.variable("result")
        m.inline_code = f"""
          {result.definition};
          assert(target);
          assert({self._engaged(e)});
          {element.copy(result, self._slot_var(e))};
          return {result};
        """

    with self.method(element.view_type, ("value", "view"), {"target": self}, brief="Get view of the held value",
      description="""
        Returns a constant view of the held element value. The optional must hold a value.

        @param[in] target the optional to inspect
        @return constant view of the held element value
      """) as m:
      m.inline_code = f"""
        assert(target);
        assert({self._engaged(e)});
        return {self._slot_var(e).bind(m.result)};
      """

    if element.copyable:
      with self.method(None, "set", {"target": inout(self), "element": element}, constraint=lambda: element.copyable, brief="Engage with a copy of the element",
        description="""
          Releases the currently held value when present and engages the optional with a
          copy of the given element.

          @param[in,out] target the optional to engage
          @param[in] element the element to copy
        """) as m:
        engaged_mark = self._mark(self.engaged_state)(e)
        engaged_code = f"\n          {engaged_mark};" if engaged_mark else ""
        m.inline_code = f"""
          assert(target);
          if({self._engaged(e)}) {{{destroy_slot};}}
          {element.copy(self._slot_var(e), m.element)};{engaged_code}
        """

    if element.emplaceable:
      with self.method(None, "emplace", {"target": inout(self)} | element.constructor_parameters,
        constraint=lambda: element.emplaceable,
        brief="Engage with an element constructed in place",
        description="""
          Releases the currently held value when present and constructs a new element in
          place with the forwarded parameters.

          @param[in,out] target the optional to engage
        """) as m:
        create_args = [getattr(m, name) for name in element.constructor_parameters]
        engaged_mark = self._mark(self.engaged_state)(e)
        engaged_code = f"\n          {engaged_mark};" if engaged_mark else ""
        m.inline_code = f"""
          assert(target);
          if({self._engaged(e)}) {{{destroy_slot};}}
          {element.create(self._slot_var(e), *create_args)};{engaged_code}
        """

    with self.method(None, "reset", {"target": inout(self)}, brief="Release the value and enter the empty state",
      description="""
        Releases the currently held value when present and brings the optional into the
        empty state.

        @param[in,out] target the optional to reset
      """) as m:
      m.inline_code = f"""
        assert(target);
        if({self._engaged(e)}) {{{destroy_slot};}}
        {self._mark(0)(e)};
      """

    if len(self.sentinel_states) > 1:
      with self.method(None, ("set", "state"), {"target": inout(self), "state": "int"}, brief="Transition to one of the named states",
        description="""
          Brings the optional into the given state releasing the currently held value when
          present.

          @param[in,out] target the optional to transition
          @param[in] state the state to enter
        """) as m:
        marks = [f"if({m.state} == {s}) {{{self._mark(s)(e)};}}" for s in self.sentinel_states]
        m.inline_code = f"""
          assert(target);
          assert({m.state} >= 0 && {m.state} < {self.nstates});
          if({self._engaged(e)}) {{
            {{{destroy_slot};}}
          }}
          {" ".join(marks)}
        """

  # Marks the target storage with the state the source storage is in
  def _mark_states_from(self, target_e, source_e):
    marks = [f"if({self._is(s)(source_e)}) {{{self._mark(s)(target_e)};}}" for s in self.sentinel_states]
    engaged_mark = self._mark(self.engaged_state)(target_e)
    else_clause = f" else {{{engaged_mark};}}" if engaged_mark else ""
    return f"{' '.join(marks)}{else_clause}"

  # Renders the state index of the storage as a C expression
  def _state_chain(self, e):
    chain = [f"{self._is(s)(e)} ? {s} : " for s in self.sentinel_states]
    return f"({''.join(chain)}{self.engaged_state})"

  def _slot_var(self, e):
    return self.element.variable(self._slot(e))

  @property
  def constructible(self):
    return True

  @property
  def destructible(self):
    return self.element.destructible

  @property
  def copyable(self):
    return self.element.copyable

  @property
  def comparable(self):
    return self.element.comparable

  @property
  def orderable(self):
    return self.element.orderable

  @property
  def hashable(self):
    return self.element.hashable