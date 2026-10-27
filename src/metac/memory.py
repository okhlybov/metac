import functools
import metac.core
import metac.std as std
from metac.core import Type
from metac.module import Code


_allocate_code = Code(
  dependencies=(std.stdlib_h, std.assert_h, std.stdint_h, metac.core._linkage_code),
  interface="""
    /** @private */
    METAC_EXTERN void* _metac_malloc(size_t size);
    /** @private */
    METAC_EXTERN void* _metac_calloc(size_t count, size_t size);
    /** @private */
    METAC_EXTERN void* _metac_malloc_array(size_t count, size_t size);
  """,
  implementation="""
    void* _metac_malloc(size_t size) {
      void* ptr = malloc(size);
      if(!ptr && size > 0) {
        assert(0 && "malloc() returned NULL");
        abort();
      }
      return ptr;
    }
    void* _metac_calloc(size_t count, size_t size) {
      void* ptr = calloc(count, size);
      if(!ptr && count*size > 0) {
        assert(0 && "calloc() returned NULL");
        abort();
      }
      return ptr;
    }
    void* _metac_malloc_array(size_t count, size_t size) {
      /* calloc() rejects the wrapping product itself - the plain malloc path must
         check the multiplication before performing it, else a huge count wraps
         around to a small allocation and overflows it at first write */
      if(size != 0 && count > SIZE_MAX / size) {
        assert(0 && "allocation size overflow");
        abort();
      }
      return _metac_malloc(count * size);
    }
  """
)


# Generic C malloc()+free() memory manager
@functools.cache
class Manager(Code):
  
  def __init__(self, *args, **kwargs):
    super().__init__(*args, dependencies=(std.stdlib_h, _allocate_code), **kwargs)
    
  def allocate(self, element, count=1, zero=False, cast=None):
    if isinstance(element, Type):
      type = element
      size = f"sizeof({type})"
    else:
      type = None
      size = element
    if zero:
      code = f"_metac_calloc({count}, {size})"
    else:
      code = f"_metac_malloc({size})" if count == 1 else f"_metac_malloc_array({count}, {size})"
    if not cast and type:
      cast = type
    return f"({cast}*){code}" if cast else code
    
  def free(self, ptr):
    return f"free({ptr})"