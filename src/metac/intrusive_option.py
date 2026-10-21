from metac.core import _AliasRenderer
from metac.options import Option as _Option


def _normalize_pair(pair):
  if isinstance(pair, (tuple, list)) and len(pair) == 2:
    return (pair[0], pair[1])
  if isinstance(pair, dict):
    is_fn = pair.get("query") or pair.get("is")
    mark_fn = pair.get("set") or pair.get("mark")
    if is_fn is not None and mark_fn is not None:
      return (is_fn, mark_fn)
  raise ValueError(f"expected a (query, set) pair or dict, got {pair}")


def _normalize_sentinel_states(states):
  """
  Normalizes sentinel state specifications into the canonical dict:
    {"empty": (query, set), "deleted": (query, set), ...}
  where state 0 is empty and states 1+ are user-specified sentinel states.
  Position in the dict defines the state index: 0 is empty, 1+ are user states.
  """
  if not isinstance(states, dict) or not states:
    raise ValueError(f"sentinel states must be provided as a non-empty dict of (query, set) pairs, got {states}")
  return {str(k): _normalize_pair(v) for k, v in states.items()}


# The intrusive optional: the states are encoded as sentinel element values supplied
# by the user, with the engaged state being any value matching no sentinel. Exactly
# like the intrusive hash containers this trades value space for representation size.
class Option(_AliasRenderer, _Option):

  brief = "Optional value with the states encoded as sentinel element values"

  def __init__(self, name, element, states, *args, **kwargs):
    states_dict = _normalize_sentinel_states(states)
    super().__init__(name, element, *args, **kwargs)
    self._state_names = list(states_dict.keys())
    self._emitters = {i: emitters for i, emitters in enumerate(states_dict.values())}
    self.nstates = len(self._emitters)

  @property
  def sentinel_states(self):
    return list(range(len(self._emitters)))

  @property
  def engaged_state(self):
    return -1

  def _state_name(self, s):
    if 0 <= s < len(self._state_names):
      return self._state_names[s]
    return None

  def _is(self, state):
    if isinstance(state, str):
      state = self._state_names.index(state) if state in self._state_names else -1
    if state == self.engaged_state:
      return lambda e: self._engaged(e)
    is_state, _ = self._emitters[state]
    return is_state

  def _mark(self, state):
    if isinstance(state, str):
      state = self._state_names.index(state) if state in self._state_names else -1
    if state == self.engaged_state:
      # Holding a real element value IS the engaged state - the element was just put
      # in place by the caller so there is nothing to mark
      return lambda e: str()
    _, mark_state = self._emitters[state]
    return mark_state

  def _slot(self, e):
    # The element storage is the whole value of the intrusive optional
    return e

  def render_declarations(self, stream, header):
    super().render_declarations(stream, header)
    if header:
      stream.append(f"typedef {self.element} {self.name};\n")
