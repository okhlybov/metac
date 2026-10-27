import metac.std as std
from itertools import islice
from metac.memory import Manager
from metac.core import Composite, _StructRenderer, _AliasRenderer, Indirection, Callable, out, inout


#  
class _Reference(Indirection, Composite):
  
  def __init__(self, type, *args, name=None, **kwargs):
    super().__init__(type, type.name if name is None else name, *args, **kwargs)
    
  def __setup__(self):
    super().__setup__()

    self.method(Callable.Parameter(self), "new", {name: type for name, type in islice(self.type.create.parameters.items(), 1, None)}, brief="Create the reference owning a new instance of the type",
      description="""
        Allocates a new instance of the referenced type, constructs it with the given
        parameters and returns the unmanaged reference owning it. The caller is responsible
        for releasing the instance with free.

        @return the reference to the newly allocated instance - releasing this reference frees the instance
      """)
    self.macro("create", None, {"target": out(self)} | self.new.parameters, lambda target, *args: f"{target} = {self.new(*args)}")

    self.method(self, "share", {"source": self}, brief="Duplicate reference handle",
      description="""
        Returns another reference to the instance the source references without duplicating
        it or modifying ownership.

        @param[in] source the reference to share - must reference a valid instance
        @return another reference to the same instance
      """)
    self.macro_from("copy", lambda target, source: f"{target} = {self.share(source)}")
    
    self.method(None, "free", {"target": self}, brief="Free referenced instance",
      description="""
        Destroys and releases the referenced instance immediately. Any other handles
        referencing this instance become invalid unless the reference type manages shared
        ownership. A null reference is ignored.

        @param[in] target the reference to release - the instance is destroyed and its memory freed, a null reference is ignored
      """)
    self.macro_from("destroy", lambda target: self.free(target))
    
    # A moved-from reference is nulled so that destroying it afterwards is a safe no-op
    # The underlying free guards on the pointer being NULL
    self.macro_from("move", lambda target, source: f"{target} = {source}, {source} = NULL")
    # Swapping exchanges the handles in constant time
    self.swap = self.method(None, "swap", {"left": inout(Indirection(self)), "right": inout(Indirection(self))}, brief="Swap two references",
      description="""
        Exchanges the two reference handles in constant time without copying or destroying
        the referenced instances.

        @param[in,out] left the first reference
        @param[in,out] right the second reference
      """)
    with self.swap as m:
      m.inline_code = f"""
        {self} temp;
        temp = *left;
        *left = *right;
        *right = temp;
      """

    
    # Delete self attributes which arent handled by the class to force proxying
    del self.equal
    del self.compare
    del self.hash
    
  def __getattr__(self, name):
    return getattr(self.type, name)
  
  @property
  def rvalue_type(self):
    return self

  @property
  def lvalue_type(self):
    return self
  
  @property
  def view_type(self):
    return self.constness(True)


#
class Raw(_AliasRenderer, _Reference):

  brief = "Unmanaged reference to an instance"
  
  def __init__(self, *args, memory=Manager(), **kwargs):
    super().__init__(*args, **kwargs)
    self.memory = memory
    self.dependencies.update((self.memory, std.assert_h))
    
  def __setup__(self):
    super().__setup__()
    
    with self.new as m:
      result = m.result.variable("result")
      m.inline_code = f"""
        {result.definition};
        {result} = {self.memory.allocate(self.type)};
        {self.type.create(result, *m.arguments)};
        return {result};
      """
      
    with self.share as m:
      m.inline_code = f"""
        assert(source);
        return ({self}){m.source};
      """
      
    with self.free as m:
      # Raw bears no layout of its own: new() allocates the referenced type
      # directly, so free() releases exactly that allocation
      m.code = f"""
        if({m.target}) {{
          {self.type.destroy(m.target) if self.type.destructible else str()};
          {self.memory.free(f"(void*){m.target}")};
        }}
      """


#
class Counted(_StructRenderer, _Reference):
  
  brief = "Reference counted shared instance proxy type"
  
  def __init__(self, *args, memory=Manager(), **kwargs):
    super().__init__(*args, **kwargs)
    self.memory = memory
    self.dependencies.update((self.memory, std.assert_h))
    self._layout = self._decorate_component("layout")
    
  def __setup__(self):
    super().__setup__()

    self.description = """
      Reference counted shared instance proxy type: each reference is a cheap handle and the
      referenced instance lives until the last reference to it is released.
      The counter is a plain non-atomic unsigned integer - like std::rc::Rc, NOT the atomic
      std::sync::Arc - so a counted instance and its references must be confined to a single
      thread (or externally synchronized): sharing them across threads without such
      synchronization races on the count and can free the instance twice.
    """

    self.new.brief = "Create reference owning a new reference-counted instance"
    self.new.description = """
      Allocates a new instance of the referenced type with an associated reference counter,
      constructs it with the given parameters and returns the reference owning it. The instance
      lives until every reference to it is released.

      @return the reference to the newly allocated instance - releasing this reference decrements the count and frees the instance when it reaches zero
    """

    self.share.brief = "Share the instance by increasing its reference count"
    self.share.description = """
      Returns another reference to the instance the source references without duplicating
      it - increments the reference count so the referenced instance stays alive as long
      as at least one reference to it exists.

      @param[in] source the reference to share - must reference a valid instance
      @return another reference to the same instance - the shared instance stays owned by the caller as well
    """

    self.free.brief = "Decrement reference count"
    self.free.description = """
      Releases one ownership of the referenced instance by decrementing its reference count.
      The instance is destroyed and its memory freed only when the last reference to it is
      released, making this safe to pair with the sharing.

      @param[in] target the reference to release - the instance is destroyed when its last reference is released, a null reference is ignored
    """

    self.swap.description = """
      Exchanges the two reference handles in constant time without touching the reference
      counts - the instances referenced stay exactly as owned as they were.

      @param[in,out] left the first reference
      @param[in,out] right the second reference
    """
    
    with self.new as m:
      value = self.type.variable("storage->value")
      m.inline_code = f"""
        {self._layout}* storage;
        storage = {self.memory.allocate(f"sizeof({self._layout})", cast=self._layout)};
        {self.type.create(value, *m.arguments)};
        storage->count = 1;
        return ({m.result})storage;
      """
      
    with self.share as m:
      m.inline_code = f"""
        assert(source);
        ++(({self._layout}*){m.source})->count;
        return ({self}){m.source};
      """
      
    with self.free as m:
      m.inline_code = f"""
        if({m.target}) {{
          if(--(({self._layout}*){m.target})->count == 0) {{
            {self.type.destroy(m.target) if self.type.destructible else str()};
            {self.memory.free(f"({self._layout}*){m.target}")};
          }}
        }}
      """

  def _render_struct(self, stream, header):
    super()._render_struct(stream, header)
    stream.append("/** @private */\n")
    stream.append(f"""
      typedef struct {{
        {self.type} value;
        unsigned count;
      }} {self._layout};
    """)    