import unittest

import metac.core
import metac.flat_map
import metac.std as std
import metac.module
from metac.core import Template, TraitError
from metac.module import DuplicateNameError
from metac.array import Array
from metac.chained_hash_map import Map
from metac.counter import Counter
from metac.list import List
from metac.record import Record
from metac.vector import Vector


metac.core.decorator = metac.core.snake_decorator


class TestSubscription(unittest.TestCase):

  def test_subscription_factory(self):
    t = Vector[std.int]
    self.assertIs(t, Vector[std.int]) # the interned parametrizations are singletons
    self.assertIsInstance(t, Template)
    self.assertEqual(repr(t), "Vector<int>")
    self.assertEqual(t._derived_name(), "int_vector")

  def test_std_spellings(self):
    self.assertEqual(repr(Vector[std.int]), "Vector<int>")
    self.assertEqual(repr(Map[std.int, "const char*"]), "Map<int, cstring>")
    self.assertEqual(Map[std.int, "const char*"]._derived_name(), "int_cstring_map")
    self.assertEqual(repr(Map["const char*", std.double]), "Map<cstring, double>")
    self.assertEqual(Map["const char*", std.double]._derived_name(), "cstring_double_map")

  def test_builtin_types_rejected(self):
    # The Python builtins are not type spellings - the metac.std primitives
    # or the C spellings are, keeping the parameterization vocabulary explicit
    with self.assertRaises(TraitError):
      Vector[int]("values")

  def test_call_spelling(self):
    v = Vector[std.int]("values")
    self.assertIsInstance(v, Vector)
    self.assertEqual(v.name, "values")
    self.assertEqual(str(v.element), "int")
    m = Map[std.int, "const char*"]("str2int")
    self.assertEqual(str(m.element), "int")
    self.assertEqual(str(m.index), "const char*")

  def test_partial(self):
    a = Array[std.int].partial(size=8)("matrix")
    self.assertEqual((a.name, a._size), ("matrix", 8))
    self.assertIs(Array[std.int].partial(size=8), Array[std.int].partial(size=8))
    with self.assertRaises(TraitError):
      Vector[std.int].partial(element="long") # element is a type parameter, not tuning
    with self.assertRaises(TraitError):
      Array[std.int].partial(size=4).partial(size=8)
  def test_arity_and_missing(self):
    with self.assertRaises(TraitError):
      Vector[std.int, std.int]
    with self.assertRaises(TraitError):
      Array[std.int]("too_few") # the size stays call-time and is required

  def test_context_anchored_derivation(self):
    outer = List[Vector[std.int]]("scores")
    self.assertEqual(outer.element.name, "scores_int_vector")
    deep = List[Map[std.int, Vector["const char*"]]]("x")
    self.assertEqual(deep.element.name, "x_int_cstring_vector_map")
    self.assertEqual(deep.element.index.name, "x_int_cstring_vector_map_cstring_vector")

  def test_derivation_follows_the_decorator(self):
    # The derived names ride the global decoration pipeline - the camel
    # modules derive the camel spellings, not the snake ones
    saved = metac.core.decorator
    metac.core.decorator = metac.core.camel_decorator
    try:
      outer = List[Vector[std.int]]("Scores")
      self.assertEqual(outer.element.name, "ScoresIntVector")
      self.assertEqual(Vector[std.int]._derived_name(), "IntVector")
    finally:
      metac.core.decorator = saved

  def test_explicit_nesting_name(self):
    # The uniform naming rule: naming a parametrization is calling it - the
    # pre-constructed instance passes through as the parameter verbatim
    outer = List[Vector[std.int]("samples")]("s2")
    self.assertEqual(outer.element.name, "samples")
    # and a hoisted instance is shared, not re-materialized per outer
    inner = Vector[std.int]("shared")
    self.assertIs(List[inner]("a").element, inner)
    self.assertIs(List[inner]("b").element, inner)

  def test_positional_parametrization(self):
    # The classic positional spelling accepts the parametrizations as well -
    # they materialize under the same context-anchored derivation
    outer = List("y", Vector[std.int])
    self.assertEqual(outer.element.name, "y_int_vector")

  def test_shared_materialization_within_construction(self):
    # The same parametrization used by several parameters of one construction
    # materializes once (the record fields spelling)
    r = Record("r", {"a": Vector[std.int], "b": Vector[std.int]})
    self.assertIs(r.fields["a"], r.fields["b"])
    self.assertEqual(r.fields["a"].name, "r_int_vector")

  def test_counter_backend_partial(self):
    c = Counter[std.int].partial(backend=metac.flat_map.Map)("cnt")
    self.assertEqual(c.name, "cnt")
    self.assertEqual(str(c.element), "int")

  def test_duplicate_name_detection(self):
    module = metac.module.Module("dupmod")
    module.add(Vector("dup", "int"))
    # The self-typedef is the identifier-carrying declaration - any second
    # claim over it breaks the C, identical shape or not
    with self.assertRaises(DuplicateNameError):
      module.add(Vector("dup", "int"))
    with self.assertRaises(DuplicateNameError):
      module.add(Vector("dup", "double"))

  def test_closure_duplicate_detection(self):
    # The nested instantiations are referenced rather than added - the closure
    # check at the render time catches their collisions as well
    module = metac.module.Module("dupmod2")
    module.add(List("same", "int"))
    with self.assertRaises(DuplicateNameError):
      module.add(List[Vector[std.int]]("same"))

  def test_module_add_materialization(self):
    module = metac.module.Module("tplmod")
    module.add(Vector[std.int])
    self.assertEqual(sorted(e.name for e in module.entities), ["int_vector"])

  def test_default_name(self):
    v = Vector[std.int]()
    self.assertEqual(v.name, "int_vector")
    self.assertEqual(str(v.element), "int")
    a = Array[std.int].partial(size=8)()
    self.assertEqual(a.name, "int_array_size_8")

  def test_call_slot_clash(self):
    with self.assertRaises(TraitError):
      Vector[std.int]("v", element="double")

  def test_pointer_derived_name(self):
    self.assertEqual(Vector["int*"]._derived_name(), "int_ptr_vector")
    self.assertEqual(Vector["void*"]._derived_name(), "void_ptr_vector")

  def test_duplicate_detection_with_counted_reference(self):
    from metac.reference import Counted
    module = metac.module.Module("dupmod3")
    v1 = Vector("dup", "int")
    ref = Counted(v1)
    v2 = List("dup", "int")
    # Even if the non-conflicting reference is processed first, conflicting structs must be caught
    module.entities.add(ref)
    module.entities.add(v1)
    module.entities.add(v2)
    with self.assertRaises(DuplicateNameError):
      module._check_duplicate_names()


# Run tests when imported or executed directly
suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestSubscription)
runner = unittest.TextTestRunner()
result = runner.run(suite)
assert result.wasSuccessful(), f"Subscription tests failed: {result.errors} {result.failures}"

if __name__ == "__main__":
  unittest.main()
