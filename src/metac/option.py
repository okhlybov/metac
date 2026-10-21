from metac.options import Option as _Option
from metac.core import _StructRenderer


# The plain optional: the state is kept in an integer state stored alongside the value.
# State -1 is the engaged state holding the element value; state 0 is the technically
# specified empty state; states 1 and beyond are user-defined value-less states.
class Option(_StructRenderer, _Option):

  brief = "Optional value holding either an element or a state state"

  def __init__(self, name, element, *args, states=1, **kwargs):
    super().__init__(name, element, *args, **kwargs)
    if isinstance(states, (list, tuple)):
      self._state_names = ["empty"] + [str(s) for s in states]
      self.nstates = len(self._state_names)
    elif isinstance(states, dict):
      self._state_names = list(states.keys())
      self.nstates = len(self._state_names)
    else:
      self.nstates = int(states)
      self._state_names = ["empty"] + [f"state_{i}" for i in range(1, self.nstates)]
    if self.nstates < 1:
      raise ValueError(f"an optional needs at least the empty state, got {self.nstates}")

  def _state_name(self, s):
    if 0 <= s < len(self._state_names):
      return self._state_names[s]
    return None

  def _is(self, state):
    if isinstance(state, str):
      state = self._state_names.index(state) if state in self._state_names else -1
    return lambda e: f"{e}.state == {state}"

  def _mark(self, state):
    if isinstance(state, str):
      state = self._state_names.index(state) if state in self._state_names else -1
    return lambda e: f"{e}.state = {state}"

  def _slot(self, e):
    return f"{e}.value"

  def _render_struct(self, stream, header):
    super()._render_struct(stream, header)
    stream.append(f"""
      struct {self.name} {{
        {self.element} value; /**< @private */
        int state; /**< @private */
      }};
    """)
