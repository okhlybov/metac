import sys
import metac.core
import metac.std as std
from metac.module import Code
from metac.core import out, Macro
from metac.random import RandomSeeder


#
seeder = RandomSeeder()


#
class _IncrementalHasher(Code):
  
  def __init__(self, seeder=None, dependencies=(), **kwargs):
    self.seeder = seeder if seeder else sys.modules[__name__].seeder
    super().__init__(dependencies=(*dependencies, self.seeder), **kwargs)
    self.state_t = std.size_t
    self.create = Macro(None, {"state": out(self.state_t)}, lambda state: f"{state} = {self.seeder.seed}")
    self.destroy = Macro(None, {"state": out(self.state_t)}, lambda source: str())
    self.hash = Macro(std.size_t, {"state": self.state_t}, lambda state: state)
    # self.update =

  
# Incremental xor+rot hasher for ordered data types
class XorRot(_IncrementalHasher):

  def __init__(self, dependencies=(), **kwargs):
    super().__init__(dependencies=(*dependencies, _rotl_code))
    self.update = Macro(None, {"state": out(self.state_t), "hash": std.size_t}, lambda state, hash: f"{state} ^= _metac_rotl({hash})")
    

_rotl_code = Code(dependencies=(std.limits_h, std.size_t, metac.core._linkage_code), interface=f"""
    /** @private */
    METAC_STATIC_INLINE
    size_t _metac_rotl(size_t value) {{
      return (value << 1) | (value >> (sizeof(size_t)*CHAR_BIT - 1));
    }}
  """)
    
    
# Incremental xor hasher for unordered data types
class Xor(_IncrementalHasher):

  def __init__(self, **kwargs):
    super().__init__(**kwargs)
    self.update = Macro(None, {"state": out(self.state_t), "hash": std.size_t}, lambda state, hash: f"{state} ^= {hash}")