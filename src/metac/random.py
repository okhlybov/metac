import functools
import metac.core
import metac.std as std
from metac.module import Entity, Code


#
@functools.cache
class StaticSeeder(Entity):
  
  def __init__(self, value=0):
    super().__init__()
    self.seed = value
  

#
hash = Code(dependencies=(metac.core._linkage_code, std.size_t), interface="""
  /** @private */
  METAC_STATIC_INLINE
  size_t _metac_hash(size_t key) {
    /*
      Thomas Wang's mixing
      http://web.archive.org/web/20071223173210/http://www.concentric.net/~Ttwang/tech/inthash.htm
    */
    if(sizeof(size_t) >= 8) {
      key = (~key) + (key << 21);
      key = key ^ (key >> 24);
      key = (key + (key << 3)) + (key << 8);
      key = key ^ (key >> 14);
      key = (key + (key << 2)) + (key << 4);
      key = key ^ (key >> 28);
      key = key + (key << 31);
    } else {
      key = (key ^ 61) ^ (key >> 16);
      key = key + (key << 3);
      key = key ^ (key >> 4);
      key = key * 0x27d4eb2d;
      key = key ^ (key >> 15);
    }
    return key;  
  }
""")


@functools.cache
class RandomSeeder(Code):

  def __init__(self):
    super().__init__(interface="""
      /** @private */
      METAC_EXTERN size_t _metac_seed;
      /** @private */
      METAC_EXTERN
        void
      #if defined(_WIN32) && (defined(__POCC__) || defined(METAC_MSVC) || defined(__BORLANDC__) || defined(__TURBOC__) || defined(__DMC__) || defined(__SC__) || defined(__LCC__))
        __cdecl
      #endif
      _metac_randomize_seed(void);
    """, implementation="""
      size_t _metac_seed = 1;
      #include <time.h>
      #ifdef _WIN32
        #include <process.h>
        #if defined(METAC_MSVC) || defined(__POCC__)
          #define _metac_getpid() ((unsigned)_getpid())
        #else
          #define _metac_getpid() ((unsigned)getpid())
        #endif
      #else
        #include <unistd.h>
        #define _metac_getpid() ((unsigned)getpid())
      #endif
      #if defined(__cplusplus)
        namespace {
          struct _MetacRandomSeederInit {
            _MetacRandomSeederInit() { _metac_randomize_seed(); }
          } _metac_random_seeder_init;
        }
      #elif defined(__GNUC__) || defined(__clang__) || defined(__TINYC__) || defined(__INTEL_COMPILER) || defined(__INTEL_LLVM_COMPILER) || defined(__ARMCC_VERSION) || defined(__ARMCOMPILER_VERSION) || defined(__ARMCC_COMPILER_VERSION) || defined(__xlC__)
        void _metac_randomize_seed(void) __attribute__((__constructor__));
      #elif defined(__PGI) || defined(__NVCOMPILER)
        #pragma init (_metac_randomize_seed)
      #elif defined(__POCC__)
        #pragma startup _metac_randomize_seed
      #elif defined(__BORLANDC__) || defined(__TURBOC__)
        #pragma startup _metac_randomize_seed 100
      #elif defined(__DMC__) || defined(__SC__)
        #pragma startup _metac_randomize_seed
      #elif defined(__LCC__)
        #pragma startup _metac_randomize_seed
      #elif defined(METAC_MSVC)
        #pragma section(".CRT$XCU", read)
        __declspec(allocate(".CRT$XCU"))
        static void (*_metac_init_ptr)(void) = _metac_randomize_seed;
      #else
        #if defined(__STDC_VERSION__) && __STDC_VERSION__ >= 199901L
          _Pragma("warning: _metac_randomize_seed() will not be called automatically; call it manually from main() or compile as C++")
        #endif
      #endif
      static unsigned _metac_entropy_word(void) {
        #if defined(__POCC__)
          /* Pelles C check comes first as it might define _MSC_VER in /Ze mode */
          unsigned word;
          if(_rand_s(&word) == 0) return word;
        #elif defined(METAC_MSVC)
          /* Genuine MSVC CRT provides rand_s() */
          unsigned word;
          if(rand_s(&word) == 0) return word;
        #elif (defined(__MINGW32__) || defined(__MINGW64__)) && (defined(_UCRT) || (defined(__STDC_VERSION__) && __STDC_VERSION__ >= 201410L))
          /* MinGW-w64 with UCRT */
          unsigned word;
          if(rand_s(&word) == 0) return word;
        #endif

        /* Standard-compliant ISO C11 high-resolution time entropy */
        #if defined(TIME_UTC) || (defined(__STDC_VERSION__) && __STDC_VERSION__ >= 201112L)
          struct timespec ts;
          if(timespec_get(&ts, TIME_UTC)) {
            return (unsigned)(ts.tv_nsec ^ _metac_getpid() ^ (unsigned)ts.tv_sec);
          }
        #elif defined(_POSIX_C_SOURCE) && _POSIX_C_SOURCE >= 200809L
          struct timespec ts;
          #if defined(CLOCK_REALTIME)
            clock_gettime(CLOCK_REALTIME, &ts);
          #else
            clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &ts);
          #endif
          return (unsigned)(ts.tv_nsec ^ _metac_getpid());
        #endif

        /* Universal fallback */
        return (unsigned)(time(NULL) ^ _metac_getpid() ^ clock());
      }
      void
      #if defined(_WIN32) && (defined(__POCC__) || defined(METAC_MSVC) || defined(__BORLANDC__) || defined(__TURBOC__) || defined(__DMC__) || defined(__SC__) || defined(__LCC__))
        __cdecl
      #endif
      _metac_randomize_seed() {
        _metac_seed = (size_t)_metac_entropy_word();
        if(sizeof(size_t) > sizeof(unsigned)) {
          _metac_seed <<= (sizeof(size_t) - sizeof(unsigned))*CHAR_BIT;
          _metac_seed ^= (size_t)_metac_entropy_word();
        }
        _metac_seed = _metac_hash(_metac_seed);
      }
    """, dependencies=(metac.core._linkage_code, std.stdlib_h, std.size_t, std.limits_h, hash))
    self.seed = "_metac_seed"


#
# Pointer-address-bound pseudo-random priority generator: derives a stable pseudo-random
# size_t value solely from an object address mixed with the per-process seed. The address
# is expected to remain unchanged during the whole lifetime of the object which makes the
# value reusable on demand without any explicit storage. Note that the generator provides
# statistical (not cryptographic) randomization thus a strong hasher is advised
@functools.cache
class Randomizer(Code):

  def __init__(self, dependencies=(), **kwargs):
    self._entity_t = metac.core.Indirection("void", constant=True)
    super().__init__(interface=f"""
      /** @private */
      METAC_STATIC_INLINE
      size_t _metac_random_priority(const void* entity) {{
        return _metac_hash(_metac_seed ^ (size_t)entity);
      }}
    """, dependencies=(*dependencies, metac.core._linkage_code, std.size_t, RandomSeeder(), hash))

  # Entity is either a bare C side expression rendered as is or a typed value
  # of pointer type subjected to the regular indirection calculation
  def priority(self, entity):
    if isinstance(entity, str):
      value = entity
    else:
      value = entity.bind(self._entity_t)
    return f"_metac_random_priority({value})"