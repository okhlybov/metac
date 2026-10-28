import metac.std as std
from metac.hash import XorRot
from metac.core import out, _type
from metac.core import Composite, _StructRenderer, Primitive, Indirection


#
class Record(_StructRenderer, Composite):
  
  brief = "Structure container holding a number of typed values"
  
  def __init__(self, name, fields, *args, hasher=XorRot(), getters=True, setters=True, views=True, opaque=True, dependencies=(), **kwargs):
    super().__init__(name, *args, dependencies=(*dependencies, std.assert_h, hasher), **kwargs)
    self.fields = {str(name): _type(type) for name, type in fields.items()}
    self.hasher = hasher
    self.getters = getters
    self.setters = setters
    # The borrowing field views generate alongside the readers unless the record
    # supplies hand-rolled ones (e.g. the multimap entry aliases its views) -
    # the flag lets such records opt out instead of colliding
    self.views = views
    self.opaque = opaque
    self.dependencies.update(self.fields.values())

  def __setup__(self):
    super().__setup__()
    
    # FIXME assert arguments when they are pointers
    
    # The member-wise bodies are built lazily: the members of the records failing the
    # respective trait have their operations inactive so the eager construction would
    # render them disabled - the constraints gate the rendering alone
    with self.create as m:
      def _create(m):
        code = []
        target = f"({m.target.bind(self)})"
        for field, type in self.fields.items():
          code.append(type.create(type.variable(f"{target}.{field}")))
          code.append(";")
        return str().join([str(x) for x in code])
      m.inline_code = _create

    with self.destroy as m:
      def _destroy(m):
        code = []
        target = f"({m.target.bind(self)})"
        for field, type in self.fields.items():
          if type.destructible:
            code.append(type.destroy(type.variable(f"{target}.{field}")))
            code.append(";")
        return str().join([str(x) for x in code])
      m.inline_code = _destroy

    with self.equal as m:
      def _equal(m):
        xs = []
        left = f"({m.left.bind(self)})"
        right = f"({m.right.bind(self)})"
        for field, type in self.fields.items():
          xs.append(str(type.equal(type.variable(f"{left}.{field}"), type.variable(f"{right}.{field}"))))
        return str().join(["return ", " && ".join(xs if xs else ["1"]), ";"])
      m.inline_code = _equal

    with self.copy as m:
      def _copy(m):
        code = []
        target = f"({m.target.bind(self)})"
        source = f"({m.source.bind(self)})"
        for field, type in self.fields.items():
          code.append(type.copy(type.variable(f"{target}.{field}"), type.variable(f"{source}.{field}")))
          code.append(";")
        return str().join([str(x) for x in code])
      m.inline_code = _copy

    with self.move as m:
      def _move(m):
        # Built lazily: the fields of the non movable records have their moves inactive
        code = []
        target = f"({m.target.bind(self)})"
        source = f"({m.source.bind(self)})"
        for field, type in self.fields.items():
          code.append(type.move(type.variable(f"{target}.{field}"), type.variable(f"{source}.{field}")))
          code.append(";")
        return str().join([str(x) for x in code])
      m.inline_code = _move

    with self.hash as m:
      def _hash(m):
        code = []
        target = f"({m.target.bind(self)})"
        state = self.hasher.state_t.variable("state")
        code.append(f"{state.definition}; size_t result; {self.hasher.create(state)};")
        for field, type in self.fields.items():
          code.append(self.hasher.update(state, type.hash(type.variable(f"{target}.{field}"))))
          code.append(";")
        code.append(f"result = {self.hasher.hash(state)}; {self.hasher.destroy(state)}; return result;")
        return str().join([str(x) for x in code])
      m.code = _hash

    if self.getters:
      for field, type in self.fields.items():
        self._add_reader(type, field)
        if self.views:
          self._add_view(type, field)

    if self.setters:
      for field, type in self.fields.items():
        self._add_writer(type, field)
        self._add_emplace_writer(type, field)

  def _add_reader(self, type, field):
    with self.method(type, field, {"target": self}, attribute=("get", field), visibility=self.visibility, constraint=lambda: type.copyable, brief=f"Get the {field} field",
      description=f"""
        Returns an owned copy of the {field} field of the record.

        @param[in] target the record to read
        @return a copy of the {field} field
      """) as m:
      def _reader_code(m):
        result = m.result.variable("result")
        target = f"({m.target.bind(self)})"
        return f"""
          {result.definition};
          {type.copy(result, type.variable(f"{target}.{field}"))};
          return {result};
        """
      m.inline_code = _reader_code

  def _add_view(self, type, field):
    # The borrowing counterpart of the copying reader - uniform with the variant's
    # alternative views; unlike the reader it carries no constraint, so the
    # non-copyable fields stay observable and the heavy ones avoid the clone
    with self.method(type.view_type, (field, "view"), {"target": self}, attribute=("get", field, "view"), visibility=self.visibility, brief=f"Get view of the {field} field",
      description=f"""
        Returns a constant view of the {field} field of the record without copying it.
        The view is valid while the record keeps the field - any setter or the record
        destruction invalidates it.

        @param[in] target the record to read
        @return a constant view of the {field} field, valid while the record keeps the field
      """) as m:
      def _view_code(m):
        target = f"({m.target.bind(self)})"
        return f"""
          return {type.variable(f"{target}.{field}").bind(m.result)};
        """
      m.inline_code = _view_code

  def _add_writer(self, type, field):
    # The composite fields pass the value by pointer, so the exact self-assignment
    # (the view of the very field fed into its own setter) is recognizable and
    # neutralized as the no-op it means; the value-passed primitives cannot alias
    self_aliasing = isinstance(type, Composite) and not isinstance(type, (Primitive, Indirection))
    brief_note = " Assigning the field to itself through its own view is a recognized no-op." if self_aliasing else ""
    with self.method(None, ("set", field), {"target": out(self), "value": type}, visibility=self.visibility, constraint=lambda: type.copyable, brief=f"Set the {field} field",
      description=f"""
        Replaces the contents of the {field} field with the given value - the previously
        held field value is destroyed first.{brief_note}

        @param[out] target the record to update
        @param[in] value the value to store into the {field} field - the previous field value is destroyed
      """) as m:
      def _writer_code(m):
        target = f"({m.target.bind(self)})"
        destroy_field = type.destroy(type.variable(f"{target}.{field}")) if type.destructible else str()
        body = f"""
          {destroy_field};
          {type.copy(type.variable(f"{target}.{field}"), "value")};
        """
        if self_aliasing:
          body = f"""
            if(&{target}.{field} != value) {{{body}}}
          """
        return body
      m.inline_code = _writer_code

  def _add_emplace_writer(self, type, field):
    with self.method(None, ("emplace", field), {"target": out(self)} | type.constructor_parameters, visibility=self.visibility, constraint=lambda: type.emplaceable, brief=f"Construct the {field} field in place",
      description=f"""
        Constructs the {field} field in place with the forwarded parameters - the previously
        held field value is destroyed first.

        @param[out] target the record to update
      """) as m:
      def _emplace_code(m):
        create_args = [getattr(m, name) for name in type.constructor_parameters]
        target = f"({m.target.bind(self)})"
        destroy_field = type.destroy(type.variable(f"{target}.{field}")) if type.destructible else ""
        return f"""
          {destroy_field};
          {type.create(type.variable(f"{target}.{field}"), *create_args)};
        """
      m.inline_code = _emplace_code

  def _getter_name(self, field):
    return self.decorate(field)
    
  def _setter_name(self, field):
    return self.decorate("set", field)

  def _render_struct(self, stream, header):
    super()._render_struct(stream, header)
    stream.append(f"struct {self.name} {{\n")
    for field, type in self.fields.items():
      stream.append(f"{type} {field};")
      if not self.internal:
        if self.opaque or self.private:
          stream.append("/**< @private */\n")
        else:
          stream.append("/**< @public */\n")
    stream.append("};\n")
    
  @property
  def constructible(self):
    return all(type.constructible for type in self.fields.values())

  @property
  def destructible(self):
    return any(type.destructible for type in self.fields.values())

  @property
  def comparable(self):
    return all(type.comparable for type in self.fields.values())
  
  @property
  def copyable(self):
    return all(type.copyable for type in self.fields.values())

  @property
  def moveable(self):
    return all(type.moveable for type in self.fields.values())

  @property
  def swappable(self):
    return all(type.swappable for type in self.fields.values())

  @property
  def hashable(self):
    return all(type.hashable for type in self.fields.values())

  @property
  def orderable(self):
    return False