import re
import sys
import textwrap
import functools
import types
import typing
import inspect
from metac.module import Entity, Code, SystemHeader
from collections.abc import Iterable # substitute for missing iterable()


_type_rxcache = [] # [ (rx, type) ]
_type_cache = {} # { name: type }


def _type2type(obj):
  return obj if isinstance(obj, Type) else None


def _str2type(obj):
  if isinstance(obj, str):
    for rx, type in _type_rxcache:
      if rx.match(obj):
        _type_cache[type.name] = type
        return type
    if obj in _type_cache:
      return _type_cache[obj]
    return Primitive(obj)
  return None


#
def _type(obj):
  for c in (_type2type, _str2type):
    if x := c(obj):
      return x
  raise TypeError(f"{obj} is not convertible to Type")


#
def _value(obj):
  match obj:
    # TODO complex
    case Value(): return obj
    case int(): return Literal("int", obj)
    case float(): return Literal("double", obj)
    case str(): return Literal("int", obj) # FIXME actually this should be borrowing the target's type
  raise TypeError(f"{obj} is not convertible to Value")


#
def _parameter(obj):
  match obj:
    case Callable.Parameter(): return obj
    case _: return Callable.In(obj)


#
def _result(obj):
  match obj:
    case Callable.Parameter(): return obj
    case _: return Callable.Result(_type(obj)) # The result is a value owned by the caller - pairs with the view_type used for borrowing


#
_intersection_cache = {}


class _IntersectionMetaclass(type):

  def __call__(cls, *args):
    flat = []
    for a in args:
      if isinstance(a, IntersectionType):
        flat.extend(a.__args__)
      else:
        flat.append(a)
    dedup = []
    for a in flat:
      if a not in dedup:
        dedup.append(a)
    key = frozenset(dedup)
    if key in _intersection_cache:
      return _intersection_cache[key]
    name = " & ".join(getattr(a, "__name__", str(a)) for a in dedup)
    inst = super().__call__(name, (), {})
    inst.__args__ = tuple(dedup)
    _intersection_cache[key] = inst
    return inst


class IntersectionType(type, metaclass=_IntersectionMetaclass):
  """Represents a type intersection (T1 & T2 & ...) using Python type protocol."""

  def __instancecheck__(cls, instance):
    return all(isinstance(instance, t) for t in cls.__args__)

  def __subclasscheck__(cls, subclass):
    return all(issubclass(subclass, t) for t in cls.__args__)

  def require(cls, other, *args, **kwargs):
    return require(other, cls)

  def __and__(cls, other):
    return IntersectionType(*cls.__args__, other)

  def __rand__(cls, other):
    return IntersectionType(other, *cls.__args__)

  def __repr__(cls):
    return cls.__name__

  def __eq__(cls, other):
    if isinstance(other, IntersectionType):
      return set(cls.__args__) == set(other.__args__)
    return False

  def __hash__(cls):
    return hash(frozenset(cls.__args__))


class _Contract(type):
  """Metaclass adding type intersection (&) to types."""

  def __and__(cls, other):
    return IntersectionType(cls, other)

  def __rand__(cls, other):
    return IntersectionType(other, cls)


def _contract_name(contract):
  if isinstance(contract, _Coercion):
    return repr(contract)
  if isinstance(contract, IntersectionType):
    return " & ".join(_contract_name(a) for a in contract.__args__)
  origin = typing.get_origin(contract)
  if origin is typing.Union or isinstance(contract, types.UnionType):
    args = typing.get_args(contract) if origin is typing.Union else contract.__args__
    return " | ".join(_contract_name(a) for a in args)
  return getattr(contract, "__name__", str(contract))


class _Coercion(type):
  """Metaclass for explicit custom type _Coercions: (source) -> (target)."""

  def __instancecheck__(cls, instance):
    if not satisfies(instance, cls.source):
      return False
    try:
      coerced = _type(instance) if isinstance(instance, str) else instance
    except Exception:
      return False
    return satisfies(coerced, cls.target)

  def __subclasscheck__(cls, subclass):
    try:
      if issubclass(subclass, Type):
        return satisfies(subclass, cls.target)
    except TypeError:
      pass
    return False

  def __rshift__(cls, other):
    return _Coercion("_Coercion", (), {"source": cls.target, "target": other})

  def require(cls, other, *args, **kwargs):
    return require(other, cls)

  def __repr__(cls):
    return f"({_contract_name(cls.source)}) -> ({_contract_name(cls.target)})"


def _corce(source, target):
  return _Coercion("_Coercion", (), {"source": source, "target": target})


class _CoerceMetaclass(type):

  def __getitem__(cls, item):
    if isinstance(item, tuple):
      if len(item) == 2:
        return _corce(item[0], item[1])
      raise ValueError("Coerce[...] takes 1 or 2 arguments")
    T = globals().get("Type")
    source = (str | T) if T is not None else str
    return _corce(source, item)


class Coerce(metaclass=_CoerceMetaclass):
  """Explicit custom type _Coercion: Coerce[Target] or Coerce[Source, Target]."""
  pass


class _TraitMetaclass(_Contract):
  """Metaclass for trait protocols (Comparable, Orderable, Hashable, etc.)."""

  def __instancecheck__(cls, instance):
    if isinstance(instance, type):
      return cls.__subclasscheck__(instance)
    val = getattr(instance, cls._instance_trait, False)
    if isinstance(val, property):
      return False
    return bool(val)

  def __subclasscheck__(cls, subclass):
    val = getattr(subclass, cls._instance_trait, False)
    if isinstance(val, property):
      return False
    return bool(val)

  def require(cls, other, *args, **kwargs):
    return require(other, cls)

  def __repr__(cls):
    return cls.__name__


class _Trait(metaclass=_TraitMetaclass):
  pass


class Constructible(_Trait):
  _instance_trait = "constructible"


class DefaultConstructible(_Trait):
  _instance_trait = "default_constructible"


class Emplaceable(_Trait):
  _instance_trait = "emplaceable"


class Destructible(_Trait):
  _instance_trait = "destructible"


class Copyable(_Trait):
  _instance_trait = "copyable"


class Moveable(_Trait):
  _instance_trait = "moveable"


class Swappable(_Trait):
  _instance_trait = "swappable"


class Comparable(_Trait):
  _instance_trait = "comparable"


class Orderable(_Trait):
  _instance_trait = "orderable"


class Hashable(_Trait):
  _instance_trait = "hashable"


class ZeroInitializable(_Trait):
  _instance_trait = "zero_initializable"


class _StageConstructorMetaclass(_Contract):

  def __call__(cls, *args, **kwargs):
    obj = super().__call__(*args, **kwargs)
    obj.__setup__()
    obj.__register__()
    return obj


# Descriptor binding to the class when accessed on the class and to the instance when accessed on an instance
class binder:

  def __init__(self, fn):
    self.fn = fn

  def __get__(self, instance, owner=None):
    target = owner if instance is None else instance
    return functools.partial(self.fn, target)


# Mixin for types which support all operations
class _Traitful:

  @property
  def constructible(self):
    return True
  
  @property
  def default_constructible(self):
    return self.constructible and getattr(self, "create", None) is not None and len(self.create.parameters) == 1

  @property
  def emplaceable(self):
    return self.constructible

  @property
  def constructor_parameters(self):
    if not hasattr(self, "create") or self.create is None or not hasattr(self.create, "parameters"):
      return {}
    from itertools import islice
    return {str(name): param for name, param in islice(self.create.parameters.items(), 1, None)}

  @property
  def destructible(self):
    return True

  # The value traits are derived from the presence of the operation implementations:
  # a type carries whatever operations it has actually defined and nothing else. The
  # optimistic defaults would render the declarations without the bodies crashing the
  # generation or linking for the types which never supplied them
  @property
  def copyable(self):
    return _defined(getattr(self, "copy", None))

  @property
  def moveable(self):
    # A type is movable when it either supplies its own move or when the move is derivable:
    # the default construction manufactures the pristine shell which the swap then exchanges
    # with the source leaving the source in the pristine state as well
    if _defined(getattr(self, "move", None)):
      return True
    return self.default_constructible and self.swappable

  # Swappability is the weaker exchange trait: swapping exchanges the representations of two
  # complete values so both sides remain valid afterwards - unlike move it requires no pristine
  # state to be left behind and is therefore available to some types which are not moveable
  @property
  def swappable(self):
    return True

  @property
  def comparable(self):
    return _defined(getattr(self, "equal", None))

  @property
  def orderable(self):
    return _defined(getattr(self, "compare", None))

  @property
  def hashable(self):
    return _defined(getattr(self, "hash", None))

  # The zero representation of the value is a valid pristine state which makes the bulk
  # default initialization possible through the zeroed allocations alone
  @property
  def zero_initializable(self):
    return False

  # Fluent requirement check on the target type or instance
  @binder
  def require(obj, contract, *args, **kwargs):
    return require(obj, contract)


class TraitError(TypeError, ValueError):
  pass


def satisfies(target, contract):
  if isinstance(target, type):
    try:
      return issubclass(target, contract)
    except TypeError:
      return False
  try:
    if isinstance(target, contract):
      return True
  except TypeError:
    pass
  if isinstance(target, str):
    try:
      coerced = _type(target)
      return isinstance(coerced, contract)
    except Exception:
      return False
  return False


def require(target, contract, *args, param=None, **kwargs):
  if isinstance(contract, IntersectionType):
    for t in contract.__args__:
      require(target, t, *args, param=param, **kwargs)
    return target

  if not satisfies(target, contract):
    cname = _contract_name(contract)
    tname = getattr(target, "__name__", type(target).__name__)
    prefix = f"Parameter '{param}': " if param else ""
    raise TraitError(f"{prefix}expected {cname}, got {tname}")

  return target


def _extract_coercion(contract):
  if isinstance(contract, _Coercion):
    return contract
  origin = typing.get_origin(contract)
  if origin is typing.Union or isinstance(contract, types.UnionType):
    args = typing.get_args(contract) if origin is typing.Union else contract.__args__
    for a in args:
      if isinstance(a, _Coercion):
        return a
  return None


def enforced(fn):
  sig = inspect.signature(fn)
  @functools.wraps(fn)
  def wrapper(*args, **kwargs):
    bound = sig.bind(*args, **kwargs)
    bound.apply_defaults()
    for name, val in bound.arguments.items():
      if name == "self":
        continue
      param = sig.parameters[name]
      if param.annotation is not inspect.Parameter.empty:
        contract = param.annotation
        if val is None and param.default is None:
          continue
        require(val, contract, param=name)
        coercion = _extract_coercion(contract)
        if coercion is not None and isinstance(val, str) and satisfies(val, coercion):
          bound.arguments[name] = _type(val)
    return fn(*bound.args, **bound.kwargs)
  return wrapper




class _VisibilityManager:

  def __init__(self, *args, visibility="public", **kwargs):
    super().__init__(*args, **kwargs)
    self.visibility = visibility

  @property
  def public(self):
    return self.visibility == "public"
  
  @property
  def private(self):
    return self.visibility == "private"

  @property
  def internal(self):
    return self.visibility == "internal"


_optional_group_names = {
  "sorting_operations": "Sortable",
  "bisection_operations": "Bisectable",
  "algebraic_operations": "AlgebraicSet",
  "formatting_operations": "Formatting",
}


def _optional_group_note(group):
  return f"An optional operation belonging to the {_optional_group_names.get(group)} function group."


class _Documented(Entity, _VisibilityManager):
  
  def __init__(self, *args, brief=None, description=None, optional_group=None, **kwargs):
    super().__init__(*args, **kwargs)
    self.__manage_attr("brief", brief)
    self.__manage_attr("description", description)
    self.__manage_attr("optional_group", optional_group)

  def __manage_attr(self, attr, value):
    if value:
      setattr(self, attr, value)
    elif not hasattr(self.__class__, attr):
      setattr(self, attr, None)

  # Display name of the type in the rendered documentation. The default is the
  # exact C identifier so the generated markup references the concrete expanded
  # symbols; the generic (template-like) presentation is supplied by the
  # documentation sub-project which overrides this property per type
  @property
  def _doxygen_type(self):
    return self.name if hasattr(self, "name") else str(self)
  
  def _render_documentation(self, stream, header):
    if self.public:
      # If no brief is specified, this means no description as well as the most likely case
      if self.brief:
        stream.append(f"/** @public\n@brief {self.brief}\n")
        self._render_description(stream)
        stream.append("*/\n")
      else:
        stream.append("/** @public\n")
        self._render_description(stream)
        stream.append("*/\n")
    elif header:
      stream.append("/** @private */\n")

  def _render_description(self, stream):
    if self.description:
      # The descriptions are authored nested into the Python source indentation which
      # Doxygen's Markdown would otherwise treat as the indented code blocks relative
      # to the least indented lines of the comment - leaving the embedded commands
      # unrecognized and rendered verbatim - so normalize the common prefix away
      stream.append(textwrap.dedent(self.description))
    if self.optional_group:
      stream.append(f"\n_{_optional_group_note(self.optional_group)}_\n")


#
class _GroupRenderer(_Documented):

  # A documented type owning a doxygen group. The group identifier is the type
  # name so the member @ingroup references and the @defgroup declaration always
  # agree while the group title carries the display name of the type
  def _render_description(self, stream):
    super()._render_description(stream)
    stream.append(f"\n@defgroup {self.name} {self._doxygen_type}\n")


#
class _AliasRenderer(_GroupRenderer):
  
  # Value types which bear no structure of their own (e.g. String wrapping a
  # plain char*) still render their type-level documentation and group once
  def render_declarations(self, stream, header):
    super().render_declarations(stream, header)
    if header:
      self._render_documentation(stream, header)


#
class Type(_Documented, Entity, _VisibilityManager, metaclass=_StageConstructorMetaclass):

  @classmethod
  def __class_getitem__(cls, target):
    return Coerce[str | Type, target]

  @binder
  def require(obj, contract, *args, **kwargs):
    return require(obj, contract)

  def __setup__(self):
    # Basic methods
    # The descriptions are type-agnostic because every type inherits them through
    # method_from()/macro_from() - the concrete declarations keep the parameter names
    # of these prototypes so the rendered @param entries always match the signatures
    
    self.create = Callable(None, {"target": out(self)}, constraint=lambda: self.constructible, brief="Create the value with default parameters",
      description="""
        Constructs the value in place over the uninitialized target storage. Any previous
        resources held by target must have been destroyed or reset before calling create.
        Every type inherits this operation; the concrete construction semantics are the
        ones of the type.

        @param[out] target the storage area in which to construct the value
      """)
    
    self.destroy = Callable(None, {"target": self}, constraint=lambda: self.destructible, brief="Destroy the value",
      description="""
        Releases the resources held by the value leaving it invalid - it must be reconstructed
        before any further use. Destroying a trivial value-less type is a no-op.

        @param[in] target the value to destroy - the released resources leave the value invalid
      """)
    
    self.copy = Callable(None, {"target": out(self), "source": self}, constraint=lambda: self.copyable, brief="Create a copy of the value",
      description="""
        Constructs the target as an independent copy of the source - the two values do not
        share any resources afterwards. Every type inherits this operation through the
        method_from()/macro_from() forwarding.

        @param[out] target the value to construct as the copy
        @param[in] source the value to copy
      """)
    
    self.move = Callable(None, {"target": out(self), "source": out(self)}, constraint=lambda: self.moveable, brief="Move the value to a new location",
      description="""
        Transfers the source contents to the target leaving the source in a valid empty
        state - typically a cheaper pointer transfer than the copy.

        @param[out] target the value to construct as the destination
        @param[in,out] source the value to move from - left in a valid empty state
      """)
    
    self.swap = Callable(None, {"left": inout(self), "right": inout(self)}, constraint=lambda: self.swappable, brief="Swap two values",
      description="""
        Exchanges the contents of the two values - for the handle-like types it is a constant
        time exchange of the internal pointers requiring no pristine state on either side.

        @param[in,out] left the first value
        @param[in,out] right the second value
      """)
    
    self.equal = Callable("int", {"left": self, "right": self}, constraint=lambda: self.comparable, brief="Compare two values by equality",
      description="""
        Checks the two values for equality per the type equality semantics - required to be
        consistent with the hash so the equal values always compare and hash alike.

        @param[in] left the first value
        @param[in] right the second value
        @return non-zero if the values are equal and zero otherwise
      """)
    
    self.compare = Callable("int", {"left": self, "right": self}, constraint=lambda: self.orderable, brief="Compute ordering relation of two values",
      description="""
        Establishes the strict weak ordering of the two values per the type ordering
        semantics - the ordering on which ordered containers and sorting rely.

        @param[in] left the first value
        @param[in] right the second value
        @return a negative value, zero or a positive value as the first value is less than, equal to or greater than the second one
      """)
    
    self.hash = Callable("size_t", {"target": self}, constraint=lambda: self.hashable, brief="Compute a hash of the value",
      description="""
        Computes a hash of the value over the hasher of the enclosing module - the equal
        values are guaranteed to produce the same hash making it usable by the hash-based
        containers.

        @param[in] target the value to hash
        @return the hash of the value - equal values always hash alike
      """)
    
    # Methods used by the hash-based containers
    self.hash_lookup_hash = lambda *args: self.hash(*args)
    self.hash_lookup_equal = lambda *args: self.equal(*args)
  
  def __register__(self): pass
  
  def variable(self, name):
    return Variable(self, name)

  @property
  def value_type(self):
    # A value of a type is by default its rvalue - pointer-backed types override this
    return self.rvalue_type


def _hidden_prefix(s, hidden):
  m = re.match("^(_*)(.*)", s)
  u = m.group(1)
  if not u and hidden:
    u = "_" # Prepend single underscore for a symbol marked hidden that is not already underscored
  return u + m.group(2)


# _snake_case identifier decorator
def snake_decorator(type, identifier, hidden=False):
  ids = []
  if identifier:
    ids = [identifier] if isinstance(identifier, str) else [*identifier]
  return _hidden_prefix("_".join([str(type.prefix)] + ids), hidden)


# CamelCase identifier decorator
def camel_decorator(type, identifier, hidden=False):
  ids = []
  if identifier:
    ids = [identifier] if isinstance(identifier, str) else [*identifier]
  return _hidden_prefix(str().join([str(type.prefix)] + [s[0].upper()+s[1:] for s in ids]), hidden)


# Global decorator used by all named type descentants unless overridden locally
decorator = camel_decorator


# Mixin for named types which can have methods/components/attributes etc.
class _Named(Type):
  
  def __init__(self, name, *args, prefix=None, decorator=None, **kwargs):
    super().__init__(*args, **kwargs)
    self.name = str(name)
    self.prefix = prefix if prefix else self.name
    self.decorator = decorator if decorator else sys.modules[__name__].decorator
    self.__attributes = set()


  #
  def method(self, result, identifier, parameters, *args, hidden=False, attribute=None, abstract=None, type=None, **kwargs):
    x = Function(
      result,
      self.decorate(identifier, hidden=hidden),
      parameters,
      *args,
      abstract=abstract if abstract else False,
      type=self if type is None else type,
      **kwargs
    )
    # Method by itself does not depend on its owning type - only though explicit parameters
    attribute = self._decorate_attribute(attribute if attribute else identifier)
    self.__attributes.add(attribute) # Record attribute name which holds the method object
    setattr(self, attribute, x)
    x._attribute = attribute
    return x

  #
  def macro(self, attribute, *args, **kwargs):
    self.__attributes.add(attribute) # Record attribute name which holds the method object
    setattr(self, attribute, x := Macro(*args, **kwargs))
    return x
  
  #
  def macro_from(self, attribute, *args, **kwargs):
    m = getattr(self, attribute)
    return self.macro(attribute, m._result, m._parameters, *args, **{**m._forward_kwargs, **kwargs})
    
  #
  def method_from(self, identifier, *args, attribute=None, **kwargs):
    m = getattr(self, attribute := self._decorate_attribute(attribute if attribute else identifier))
    return self.method(m._result, identifier, m._parameters, *args, constraint=m.constraint, attribute=attribute, type=self, **{**m._forward_kwargs, **kwargs})
  
  #
  def decorate(self, *args, **kwargs):
    identifier = args if len(args) > 1 else args[0]
    return self.decorator(self, identifier, **kwargs)

  def _decorate_component(self, suffix, abbreviate=True, hidden=True):
    if abbreviate:
      if isinstance(suffix, str):
        x = suffix[0]
      else:
        x = "".join([x[0] for x in suffix])
      return f"{self.decorate(None, hidden=hidden)}{x}"
    else:
      return self.decorate(suffix, hidden=hidden)
  
  def _decorate_attribute(self, identifier):
    match identifier:
      case str(): return identifier
      case list() | tuple(): return "_".join(identifier)

  # 
  def __str__(self):
    return self.name
  
  def __register__(self):
    self.references.update([t for x in self.__attributes if hasattr(self, x) and (t := getattr(self, x)) is not None and t.active])


#
class Primitive(_Named, _Traitful):

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    if not self.name in _type_cache:
      _type_cache[self.name] = self

  def __setup__(self):
    super().__setup__()
    self.macro_from("create", lambda target: f"{target} = 0")
    self.macro_from("copy", lambda target, source: f"{target} = {source}")
    self.macro_from("move", lambda target, source: f"{target} = {source}")
    self.macro_from("swap", lambda left, right: f"{{ {self} _ = {left}; {left} = {right}; {right} = _; }}")
    self.macro_from("equal", lambda left, right: f"({left} == {right})")
    self.macro_from("compare", lambda left, right: f"({left} == {right} ? 0 : ({left} < {right} ? -1 : +1))")
    self.macro_from("hash", lambda target: f"(size_t)({target})")
    
  @property
  def destructible(self):
    # Primitive types almost always bear no destructor
    return False

  @property
  def zero_initializable(self):
    # The zero representation of a primitive is a valid pristine shell - the destructor
    # bearing descendants must override this along with declaring their empty state
    return True

  @property
  def rvalue_type(self):
    return self

  @property
  def lvalue_type(self):
    return self

  @property
  def in_type(self):
    return self

  @property
  def out_type(self):
    return Indirection(self)

  @property
  def inout_type(self):
    return Indirection(self)

  @property
  def view_type(self):
    return Indirection(self, constant=True)


#
class Composite(_Named, _Traitful):

  # FIXME
  # should the composite be returned as a bare struct or constant pointer to it?
  # The latter case allows function call chaining for in parameters
  
  def __setup__(self):
    super().__setup__()
    
    self.method_from("create")
    self.method_from("destroy")
    self.method_from("copy")
    self.method_from("move")
    self.method_from("equal")
    self.method_from("compare")
    self.method_from("hash")
    
    # The swap is hidden into the translation unit - primitives themselves do not expose it publicly
    self.method_from("swap", hidden=True, visibility="internal")
    with self.swap as m:
      # Exchanging the whole representations keeps both values valid - for the containers
      # this is the O(1) bookkeeping exchange regardless of the element type
      m.code = f"""
        #ifdef __POCC__
          volatile /* A workaround for the Pelles C 14.50 optimization bug */
        #endif
        {self} temp;
        temp = *left;
        *left = *right;
        *right = temp;
      """

    # The move is derived for the types capable of manufacturing the pristine shell by the
    # default construction and exchanging the contents by swapping - the explicit move
    # definitions of the concrete types take precedence
    if self.default_constructible and self.swappable:
      with self.move as m:
        m.code = f"""
          {self.create(m.target)};
          {self.swap(m.target, m.source)};
        """

  @property
  def rvalue_type(self):
    return self

  @property
  def lvalue_type(self):
    return self

  @property
  def in_type(self):
    return Indirection(self, constant=True)

  @property
  def out_type(self):
    return Indirection(self)

  @property
  def inout_type(self):
    return Indirection(self)

  @property
  def view_type(self):
    return Indirection(self, constant=True)


class _StructRenderer(_GroupRenderer):

  opaque = True # Structs are opaque by default

  def _render_struct(self, stream, header):
    self._render_documentation(stream, header)
    if not isinstance(self, Indirection):
      if self.public:
        stream.append(f"/** @ingroup {self.name} */\n")
      else:
        stream.append("/** @private */\n")
      stream.append(f"typedef struct {self.name} {self.name};\n")
      if self.public:
        if self.opaque:
          stream.append(f"/**\n  @ingroup {self.name}\n  @brief The opaque handle representing @ref {self} value.\n*/\n")
        else:
          stream.append(f"/** @ingroup {self.name} */\n")
      else:
        stream.append("/** @private */\n")

  def render_declarations(self, stream, header):
    super().render_declarations(stream, header)
    # Structures are expected to be rendered in the interface header
    # even for internal types since they can be a part of more acessible structures
    # treated by the public inline code
    if header:
      self._render_struct(stream, header)


# Abstract class for renderable contents, basically a str-like type
class Statement:

  def __init__(self, contents, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.contents = str(contents)

  def __str__(self):
    return self.contents


def _indirection(obj):
  return t.indirection if isinstance(t := _type(obj), Indirection) else 0


def _indifference(lt, rt):
  return _indirection(lt) - _indirection(rt)


# Abstract class representing a typed value of unspecified contents which can be passed to callable
class Value:
  
  def __init__(self, type, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.type = _type(type)

  def bind(self, type):
    if (i := _indifference(self.type, type)) < 0:
      raise ValueError(f"can not dereference value {self} with & operator")
    return "*"*i


# Class representing a typed value with generic renderable contents
class Expression(Value, Statement):

  def bind(self, type):
    return super().bind(type) + self.contents


#
class Literal(Expression):
  
  def bind(self, type):
    return self.contents


#
def string(value):
  return StringLiteral(value)


#
class StringLiteral(Literal):

  def __init__(self, value, *args, **kwargs):
    super().__init__(Indirection("char", constant=True), f"\"{value}\"")


#
def char(obj):
  return CharacterLiteral(obj)


#
class CharacterLiteral(Literal):

  def __init__(self, value, *args, **kwargs):
    super().__init__("char", f"'{str(value)[0]}'")


# Class for representing the C variable
class Variable(Value):
  
  def __init__(self, type, name, **kwargs):
    super().__init__(type, **kwargs)
    self.name = str(name)

  def bind(self, type):
    i = _indifference(self.type, type)
    if i < -1:
      raise ValueError(f"too many & addressing operations requested for {self}")
    return f"&{self.name}" if i == -1 else "*"*i + self.name
    
  @property
  def definition(self):
    return f"{self.type} {self.name}"
  
  def __str__(self):
    return self.name
  

#
class Indirection(Type):

  def __init__(self, type, *args, indirection=1, constant=None, **kwargs):
    super().__init__(*args, **kwargs)
    if isinstance(t := _type(type), Indirection):
      self.type = t.type
      self.indirection = indirection + t.indirection
      self.constant = t.constant if constant is None else constant
    else:
      self.type = t
      self.indirection = indirection
      self.constant = True if constant is True else False
    self.dependencies.add(self.type)
      
  def __str__(self):
    return (f"const {self.type}" if self.constant else str(self.type)) + "*"*self.indirection

  #
  def constness(self, value):
    return Indirection(self.type, indirection=self.indirection, constant=value)
  
  #
  def variable(self, name):
    return Indirection.Variable(self, name)

  class Variable(Variable):

    def __init__(self, obj, name):
    # It makes little to no sense to define variable of const type so drop constness qualifier if it is set
      super().__init__(obj.constness(False), name)

    @property
    def definition(self):
      return f"{super().definition} = 0"
  
  @property
  def rvalue_type(self):
    return self.type

  @property
  def value_type(self):
    # A value of a pointer-backed type is the pointer itself - it must not be dereferenced
    return self

  @property
  def lvalue_type(self):
    return self.type

  @property
  def in_type(self):
    return Indirection(self.type, constant=True)

  @property
  def out_type(self):
    return Indirection(self.type, indirection=2)

  @property
  def inout_type(self):
    return self

  @property
  def view_type(self):
    # A view of a pointer-backed type is the pointer itself with const data - no extra indirection
    return self.constness(True)


#
def out(obj):
  return Callable.Out(obj)


#
def inout(obj):
  return Callable.InOut(obj)


# The function whose implementation is currently being authored (inside its
# `with` block) or rendered (inside its body evaluation) - the callables
# invoked along the way register themselves as its references so that the
# rendering can provide their declarations wherever the implementation lands
_authoring = []


# Basic callable descriptor
class Callable(_Documented):
  
  def __init__(self, result, parameters, *args, constraint=lambda: True, variadic=False, **kwargs):
    super().__init__(*args, **kwargs)
    # Capture raw parameter description to be used in modeling of the descendant types
    self._result = result
    self._parameters = parameters
    self.constraint = constraint
    self.variadic = bool(variadic)
    
  @property
  def active(self):
    return self.constraint() is True

  @property
  def _result_c(self):
    return "void" if self.result is None else str(self.result)

  @property
  def signature(self):
    params = [str(t) for t in self.parameters.values()]
    if self.variadic:
      params.append("...")
    return "%s(%s)" % (self._result_c, ", ".join(params))

  def contents(self, contents):
    if self.result is None:
      return Statement(contents)
    else:
      return Expression(self.result, contents)

  # Callable optional parameters needed to be forwarded on the callable descendant creation
  @property
  def _forward_kwargs(self):
    return {
      "brief": self.brief,
      "description": self.description,
      "optional_group": self.optional_group,
      "variadic": self.variadic,
    }

  # Create function type borrowing the signature
  def functional(self, name):
    return Functional.of(name, self)
  
  class Parameter:
    def __init__(self, type):
      self.type = _type(type)
    def resolve(self, callable):
      return self.type
      
      
  class In(Parameter):
    def resolve(self, callable):
      return callable.resolve_in(self.type)
    
  class Out(Parameter):
    def resolve(self, callable):
      return callable.resolve_out(self.type)
  
  class InOut(Parameter):
    def resolve(self, callable):
      return callable.resolve_inout(self.type)

  class Result(Parameter):
    def resolve(self, callable):
      return callable.resolve_result(self.type)


#
class _Parametrized(Callable, Entity):
  
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.result = None if self._result is None or self._result == "void" else _result(self._result).resolve(self)
    self.parameters = {str(n): _parameter(t).resolve(self) for n, t in self._parameters.items()}
    self.dependencies.update(self.parameters.values())
    if not self.result is None:
      self.dependencies.add(self.result)

  def __call__(self, *arguments):
    if _authoring:
      f = _authoring[-1]
      f.references.add(self)
      f._register_reference(self)
    if not self.active:
      raise ValueError(f"attempt to call disabled function {self}")
    if self.variadic:
      np = len(self.parameters)
      if (na := len(arguments)) < np:
        raise TypeError(f"{self} takes at least {np} parameter(s) but {na} given")
      fixed = [_value(argument).bind(type) for argument, type in zip(arguments[:np], self.parameters.values())]
      var = [str(argument) for argument in arguments[np:]]
      return [*fixed, *var]
    else:
      if (na := len(arguments)) != (np := len(self.parameters)):
        raise TypeError(f"{self} takes {np} parameter(s) but {na} given")
      return [_value(argument).bind(type) for argument, type in zip(arguments, self.parameters.values())]


class _Functional:

  def resolve_in(self, type):
    return type.in_type
  
  def resolve_out(self, type):
    return type.out_type
  
  def resolve_inout(self, type):
    return type.inout_type

  def resolve_result(self, type):
    return type.value_type

  def __str__(self):
    return self.name


# Pointer-to-function type
class Functional(Primitive, _Functional, _Parametrized, _VisibilityManager):

  @classmethod
  def of(self, name, callable, *args, **kwargs):
    return self(callable._result, name, callable._parameters, *args, **{**callable._forward_kwargs, **kwargs})

  def __init__(self, result, name, parameters, *args, **kwargs):
    super().__init__(name, result, parameters, *args, **kwargs)

  def __setup__(self):
    super().__setup__()
    self.compare = None # Function pointers are not orderable

  #
  def render_declarations(self, stream, header):
    if self.active:
      super().render_declarations(stream, header)
      if (header and not self.internal) or (not header and self.internal):
        self._render_documentation(stream, header)
        params = [str(t) for t in self.parameters.values()]
        if self.variadic:
          params.append("...")
        params_str = ", ".join(params)
        stream.append(f"typedef {self._result_c} (*{self.name})({params_str});\n")

  @property
  def orderable(self):
    return False

  def variable(self, name):
    return Functional.Variable(self, name)

  class Variable(Variable):

    def __call__(self, *arguments):
      return self.type.contents(f"{self.name}(" + ", ".join(self.type(*arguments)) + ")")


#  
class Macro(_Parametrized):
  
  @classmethod
  def of(self, callable, emitter, constraint=None, **kwargs):
    return self(callable._result, callable._parameters, emitter, constraint=constraint or callable.constraint, **{**callable._forward_kwargs, **kwargs})
  
  def __init__(self, result, parameters, emitter, **kwargs):
    super().__init__(result, parameters, **kwargs)
    self.emitter = emitter

 
  def resolve_in(self, type):
    return type.rvalue_type
  
  def resolve_out(self, type):
    return type.lvalue_type
  
  def resolve_inout(self, type):
    return type.lvalue_type

  def resolve_result(self, type):
    return type.value_type

  def __call__(self, *arguments):
    return self.contents(self.emitter(*super().__call__(*arguments)))
  
  def __str__(self):
    return "->"


def _defined(operation):
  # An operation is defined when it carries its implementation - either the macro emitter or the function body
  return isinstance(operation, Macro) or (isinstance(operation, Function) and hasattr(operation, "code"))


#
class Function(_Functional, _Parametrized, _VisibilityManager):
  
  @classmethod
  def of(self, callable, name, constraint=None, **kwargs):
    return self(callable._result, name, callable._parameters, constraint=constraint or callable.constraint, **{**callable._forward_kwargs, **kwargs})

  def __init__(self, result, name, parameters, linkage="external", abstract=None, dependencies=(), references=(), type=None, **kwargs):
    super().__init__(result, parameters, dependencies=(*dependencies, _linkage_code), references=references, **kwargs)
    self.name = str(name)
    self.linkage = linkage
    self.__abstract = abstract
    self.type = type # Object this function is attached to
    if self.type:
      self.references.add(self.type)
    self.arguments = [Variable(t, n) for n, t in self.parameters.items()] # Local variables deduced from function's formal parameters
    for x in self.arguments:
      setattr(self, x.name, x)

  def __call__(self, *arguments):
    return self.contents(f"{self.name}(" + ", ".join(super().__call__(*arguments)) + ")")

  def __repr__(self):
    return f"{self.name} {super().__repr__()}"

  @property
  def abstract(self):
    return not hasattr(self, "code") if self.__abstract is None else self.__abstract is True

  def _declaration_c(self, render_names):
    if render_names:
      params = [f"{t} {n}" for n, t in self.parameters.items()]
    else:
      params = [str(t) for t in self.parameters.values()]
    if self.variadic:
      params.append("...")
    return "%s %s(%s)" % (self._result_c, self.name, ", ".join(params))

  @property
  def _body_c(self):
    if self.abstract:
      raise ValueError(f"attempt to render definition for abstract function {self}")
    if not hasattr(self, "code"):
      raise ValueError(f"missing body of non-abstract function {self}")
    _authoring.append(self)
    self._begin_capture()
    try:
      match self.code:
        case Iterable(): cs = [str(x) for x in self.code]
        case _ if callable(self.code):
          argc = getattr(getattr(self.code, "__code__", None), "co_argcount", None)
          if argc is None:
            try:
              cs = [str(self.code(self))]
            except TypeError:
              cs = [str(self.code())]
          elif argc > 0:
            cs = [str(self.code(self))]
          else:
            cs = [str(self.code())]
        case _: cs = [str(self.code)]
    finally:
      _authoring.pop()
    return str().join(("{", *cs, "}\n"))

  @property
  def declaration(self):
    return self._declaration_c(False)

  @property
  def definition(self):
    return self._declaration_c(True) + self._body_c

  def __enter__(self):
    _authoring.append(self)
    self._begin_capture()
    return self

  def __exit__(self, *args):
    _authoring.pop()
    return False

  def body(self, func):
    self.code = func
    return func

  def inline_body(self, func):
    self.inline_code = func
    return func

  #
  def _register_reference(self, entity):
    # The invocation-captured references are tracked per the body currently
    # being authored or evaluated so that a body replacement can drop the
    # ones the previous body had captured - the explicit references=
    # declarations never pass here and so are always retained
    self._capture_log.append(entity)

  #
  def _begin_capture(self):
    if not hasattr(self, "_capture_log"):
      self._capture_log = []
    self._capture_mark = len(self._capture_log)

  #
  @property
  def code(self):
    try:
      return self._code
    except AttributeError:
      raise AttributeError(f"{self} has no code") from None

  #
  @code.setter
  def code(self, value):
    # The replacement body re-registers the references it really uses - the
    # invocations of an f-string body evaluate before the assignment while
    # the plain string bodies must declare their textual calls explicitly
    log = getattr(self, "_capture_log", [])
    mark = getattr(self, "_capture_mark", 0)
    stale = set(log[:mark]) - set(log[mark:])
    for entity in stale:
      self.references.discard(entity)
    del log[:mark]
    self._code = value

  def __inline_code(self, obj):
    self.linkage = "inline"
    self.code = obj
    
  inline_code = property(fset=__inline_code)
  
  def __external_code(self, obj):
    self.linkage = "external"
    self.code = obj

  external_code = property(fset=__external_code)
  
  @property
  def external(self):
    return self.linkage == "external"

  @property
  def inline(self):
    return self.linkage == "inline"

  @property
  def declaration(self):
    return self._declaration_c(self.public)
  
  #
  def render_declarations(self, stream, header):
    if self.active:
      super().render_declarations(stream, header)
      if (header and not self.internal) or (not header and self.internal):
        self._render_documentation(stream, header)
        if not header and self.inline:
          self._render_declaration(stream)
          self._render_definition(stream)
        else:
          self._render_declaration(stream)

  #
  def render_definitions(self, stream, header):
    if self.active:
      super().render_definitions(stream, header)
      if self.inline:
        if header and not self.internal:
          self._render_definition(stream)
      else:
        if not header:
          self._render_definition(stream)

  #
  @property
  def _source_declarations_consume(self):
    # The inline bodies render into the source declarations keeping their
    # references consumed at the translation unit scope - the external
    # function prototypes do not
    return self.internal and self.inline and not self.abstract

  #
  def _current(self):
    # The staged construction replaces the methods which the derived type
    # setups redeclare while the default bodies of the earlier phases are
    # still being evaluated, so the references captured along the way may
    # address the already replaced objects - resolve to the method which
    # the owning type attribute currently holds
    e = self
    seen = set()
    while isinstance(e, Function) and e not in seen:
      seen.add(e)
      t, a = getattr(e, "type", None), getattr(e, "_attribute", None)
      nxt = getattr(t, a, e) if t is not None and a is not None else e
      if nxt is e:
        break
      e = nxt
    return e

  #
  def _render_definition(self, stream):
    if not self.abstract:
      stream.append(self.definition)

  #
  def _render_declaration(self, stream):
    self._render_decorator(stream)
    stream.append(self.declaration)
    stream.append(";\n")

  #
  def _render_decorator(self, stream):
    stream.append(_linkage_spec_c[self.linkage])

  def _render_description(self, stream):
    super()._render_description(stream)
    # The group of the member is addressed by its identifier which is the
    # owning type name - the display name is reserved for the group title.
    # Only the public owners declare a group so the internal ones (the hidden
    # container components) must not reference a group which does not exist
    if self.type and self.type.public:
      stream.append(f"\n@ingroup {self.type.name}\n")
      
      
_linkage_spec_c = {"external": "METAC_EXTERN ", "inline": "METAC_STATIC_INLINE "}


_linkage_code = Code(interface=r"""
  #if defined(_MSC_VER)
    #if !defined(__clang__) && !defined(__INTEL_COMPILER) && !defined(__INTEL_LLVM_COMPILER) && \
        !defined(__POCC__) && !defined(__DMC__) && !defined(__SC__) && \
        !defined(__BORLANDC__) && !defined(__TURBOC__) && !defined(__LCC__) && !defined(__TINYC__)
      #if defined(__cplusplus)
        #define METAC_CXX_MSVC 1
      #else
        #define METAC_CC_MSVC 1
      #endif
      #define METAC_MSVC 1
    #else
      #if defined(__cplusplus)
        #define METAC_CXX_MSVC_COMPAT 1
      #else
        #define METAC_CC_MSVC_COMPAT 1
      #endif
      #define METAC_MSVC_COMPAT 1
    #endif
  #endif

  #if (defined(__STDC_VERSION__) && __STDC_VERSION__ >= 199901L) || \
      (defined(__cplusplus) && __cplusplus >= 201103L) || \
      (defined(_MSC_VER) && _MSC_VER >= 1900) || \
       defined(__POCC__) || defined(__TINYC__) || defined(__BORLANDC__) || \
       defined(__TURBOC__) || defined(__DMC__) || defined(__SC__) || defined(__LCC__) || \
      (!defined(__STRICT_ANSI__) && (defined(__GNUC__) || defined(__clang__)))
    #define METAC_HAS_VSNPRINTF 1
  #endif
  #if defined(METAC_MSVC) && (_MSC_VER < 1900)
    #define METAC_HAS_VSCPRINTF 1
  #endif
  #if defined(METAC_MSVC) && (_MSC_VER >= 1400) && (_MSC_VER < 1900)
    #define METAC_HAS_VSPRINTF_S 1
  #endif

  #ifndef METAC_EXTERN
    #ifdef __cplusplus
      #define METAC_EXTERN extern "C"
    #else
      #define METAC_EXTERN extern
    #endif
  #endif
  #ifndef METAC_STATIC_INLINE
    #if defined(__cplusplus) || (defined(__STDC_VERSION__) && __STDC_VERSION__ >= 199901L) || \
        (defined(__POCC_STDC_VERSION__) && __POCC_STDC_VERSION__ >= 199901L) || defined(__TINYC__)
      #define METAC_STATIC_INLINE static inline
    #elif defined(METAC_MSVC) || defined(__BORLANDC__) || defined(__TURBOC__) || defined(__DMC__) || \
        defined(__SC__) || defined(__WATCOMC__) || defined(__LCC__)
      #define METAC_STATIC_INLINE static __inline
    #elif !defined(__STRICT_ANSI__) && (defined(__GNUC__) || defined(__clang__) || defined(__INTEL_COMPILER) || defined(__INTEL_LLVM_COMPILER) || \
        defined(__POCC__) || defined(__ARMCC_VERSION) || defined(__ARMCOMPILER_VERSION) || defined(__ARMCC_COMPILER_VERSION))
      #define METAC_STATIC_INLINE static inline
    #else
      #define METAC_STATIC_INLINE static
    #endif
  #endif
""")


_stddef_h = SystemHeader("stddef.h")
_size_t = Primitive("size_t", dependencies=(_stddef_h,))

# FIXME move to a module which can import metac.std
_ceil_power2 = Code(dependencies=(_size_t, _linkage_code), definitions="""
  METAC_EXTERN
  size_t _metac_ceil_power2(size_t value);
""", implementation="""
  size_t _metac_ceil_power2(size_t value) {
    if(value == 0) return 1;
    --value;
    value |= value >> 1;
    value |= value >> 2;
    value |= value >> 4;
    value |= value >> 8;
    value |= value >> 16;
    if(sizeof(size_t) >= 8) value |= value >> 32;
    return ++value;
  }
""")