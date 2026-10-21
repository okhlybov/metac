# Programmatic concept-based test suite.
#
# Unlike the hand-crafted metac.test package whose modules each spell out their
# units, this package derives its units from the generator's own type hierarchy:
# concept-test mixins (concepts.py) emit per-method/per-invariant units for every
# concrete container instantiation registered in the matrix (matrix.py) over a
# selection of element kinds (elements.py).
#
# The framework layer is a deliberate self-contained copy of the metac.test one:
# a separate `codes` registry and a separate harness entity keep the two suites
# independent (each renders into its own module and executable) while preserving
# the familiar Unit/Type/setup/unit API.


import metac.core
import metac.module


codes = set()


metac.core.decorator = metac.core.snake_decorator


def _import_modules(package):
  import pkgutil
  import importlib
  for importer, module_name, is_pkg in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
    importlib.import_module(module_name)


def configure_module(module):
  _import_modules(metac.autotest)
  total = 0
  for c in codes:
    if isinstance(c, Type):
      total += len(c.codes)
    else:
      total += 1
  code = []
  code.append("void run_codes(void) {\n")
  if total > 0:
    code.append(f'  printf("1..{total}\\n");\n')
  else:
    code.append('  printf("1..0 # Skipped: empty test suite\\n");\n')
  for c in sorted(codes):
    module.add(c)
    code.append(f"  run_code({c.name});\n")
  code.append("}")
  module.add(metac.module.Code(definitions=str().join(code)))


# Method presence is three-valued: missing (no attribute), disabled (attribute
# is None) and trait-constrained (Callable whose constraint evaluates false).
# An operation is emittable when it exists, is enabled, is active and carries a
# body - abstract function prototypes would render declarations without
# definitions breaking the link.
def active(type, attribute):
  m = getattr(type, attribute, None)
  if m is None or not m.active:
    return False
  if hasattr(m, "abstract") and m.abstract:
    return False
  return True


class Unit(metac.module.Code):

  def __init__(self, name, dependencies=[]):
    super().__init__(dependencies=[code, *dependencies])
    self.name = name
    codes.add(self)

  def render_declarations(self, stream, header):
    super().render_declarations(stream, header)
    if header:
      stream.append(f"void {self.name}(void);")

  def render_definitions(self, stream, header):
    super().render_definitions(stream, header)
    if not header:
      stream.append(f"void {self.name}(void) {{\n")
      self.render_code(stream)
      stream.append(f"}}\n")

  def render_code(self, stream):
    desc = self.name.replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ')
    stream.append(f"""
      test_start();
      {self.code}
      test_end("{desc}");
    """)


class Type(Unit):

  def __init__(self, type, dependencies=[], name=None):
    self.type = metac.core._type(type)
    if name is None:
      name = self.type.name
    super().__init__(f"code_{name}", dependencies=[*dependencies, self.type])
    self._setup = str()
    self._cleanup = str()
    self.codes = []

  def render_code(self, stream):
    stream.append(rf'fprintf(stdout, "# --- %s\n", "{self.type}");')
    for c in self.codes:
      stream.append(c)

  def setup(self, code):
    self._setup = code

  def cleanup(self, code):
    self._cleanup = code

  def unit(self, tag, code):
    desc = f"{self.type}: {tag}".replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ')
    self.codes.append(f"""
      {{
        test_start();
        {self._setup}
        {code}
        {self._cleanup}
        test_end("{desc}");
      }}
    """)


code = metac.module.Code(
  interface=r"""
    #include <stdlib.h>
    #include <stdio.h>
    #include <string.h>
    #define TEST_MESSAGE(s) fprintf(stdout, "# *** %s\\n", s); fflush(stdout);
    #define TEST_ASSERT(x) do { if(x) {} else condition_failure("evaluated to FALSE", #x, __FILE__, __LINE__); } while(0)
    #define TEST_TRUE(x) do { if(x) {} else condition_failure("expected TRUE but got FALSE", #x, __FILE__, __LINE__); } while(0)
    #define TEST_FALSE(x) do { if(x) condition_failure("expected FALSE but got TRUE", #x, __FILE__, __LINE__); } while(0)
    #define TEST_NULL(x) do { if((x) == NULL) {} else condition_failure("expected NULL", #x, __FILE__, __LINE__); } while(0)
    #define TEST_NOT_NULL(x) do { if((x) == NULL) condition_failure("expected not NULL", #x, __FILE__, __LINE__); } while(0)
    #define TEST_EQUAL(x, y) do { if((x) == (y)) {} else equality_failure("expected equality", #x, #y, __FILE__, __LINE__); } while(0)
    #define TEST_NOT_EQUAL(x, y) do { if((x) == (y)) equality_failure("expected non-equality", #x, #y, __FILE__, __LINE__); } while(0)
    #define TEST_EQUAL_CHARS(x, y) do { if(strcmp(x, y) == 0) {} else equality_failure("expected strings equality", #x, #y, __FILE__, __LINE__); } while(0)
    #define TEST_NOT_EQUAL_CHARS(x, y) do { if(strcmp(x, y) == 0) equality_failure("expected strings non-equality", #x, #y, __FILE__, __LINE__); } while(0)
    void condition_failure(const char* message, const char* condition, const char* file, int line);
    void equality_failure(const char* message, const char* x, const char* y, const char* file, int line);
    void test_start(void);
    void test_end(const char* description);
    void run_code(void(*code)(void));
    void run_codes(void);
    extern int run, failed;
  """,
  implementation=r"""
    int run = 0, failed = 0;
    static int current_test_failed = 0;
    static const char* current_msg = NULL;
    static const char* current_cond = NULL;
    static const char* current_file = NULL;
    static int current_line = 0;
    static const char* current_x = NULL;
    static const char* current_y = NULL;

    static void print_yaml_escaped(const char* val) {
      if (!val) return;
      putchar('\'');
      for (const char* p = val; *p; ++p) {
        if (*p == '\'') {
          putchar('\'');
          putchar('\'');
        } else if (*p == '\n') {
          putchar(' ');
        } else if (*p == '\r') {
          /* ignore */
        } else {
          putchar(*p);
        }
      }
      putchar('\'');
    }

    void condition_failure(const char* message, const char* condition, const char* file, int line) {
      if (!current_test_failed) {
        current_test_failed = 1;
        current_msg = message;
        current_cond = condition;
        current_file = file;
        current_line = line;
        current_x = NULL;
        current_y = NULL;
      } else {
        fprintf(stdout, "# %s : %s (%s:%d)\n", condition, message, file, line);
        fflush(stdout);
      }
    }

    void equality_failure(const char* message, const char* x, const char* y, const char* file, int line) {
      if (!current_test_failed) {
        current_test_failed = 1;
        current_msg = message;
        current_cond = NULL;
        current_file = file;
        current_line = line;
        current_x = x;
        current_y = y;
      } else {
        fprintf(stdout, "# %s == %s : %s (%s:%d)\n", x, y, message, file, line);
        fflush(stdout);
      }
    }

    void test_start(void) {
      ++run;
      current_test_failed = 0;
      current_msg = NULL;
      current_cond = NULL;
      current_file = NULL;
      current_line = 0;
      current_x = NULL;
      current_y = NULL;
    }

    void test_end(const char* description) {
      if (!current_test_failed) {
        printf("ok %d - %s\n", run, description);
      } else {
        ++failed;
        printf("not ok %d - %s\n", run, description);
        printf("  ---\n");
        if (current_msg) {
          printf("  message: ");
          print_yaml_escaped(current_msg);
          putchar('\n');
        }
        printf("  severity: fail\n");
        if (current_file) {
          printf("  file: ");
          print_yaml_escaped(current_file);
          printf("\n  line: %d\n", current_line);
        }
        if (current_x && current_y) {
          printf("  data:\n    left: ");
          print_yaml_escaped(current_x);
          printf("\n    right: ");
          print_yaml_escaped(current_y);
          putchar('\n');
        } else if (current_cond) {
          printf("  data:\n    condition: ");
          print_yaml_escaped(current_cond);
          putchar('\n');
        }
        printf("  ...\n");
      }
      fflush(stdout);
    }

    void run_code(void(*code)(void)) {
      code();
    }

    int main(int argc, char** argv) {
      setvbuf(stdout, NULL, _IONBF, 0);
      printf("TAP version 13\n");
      run_codes();
      if(failed) {
        printf("# %d of %d test(s) failed\n", failed, run);
      } else {
        printf("# all %d test(s) passed\n", run);
      }
      exit(failed ? EXIT_FAILURE : EXIT_SUCCESS);
    }
  """
)


import metac.project
from metac.scaffolder import make_template_reader

reader = make_template_reader(__package__)


class Scaffolder:

  def __new__(cls, resources=None, parameters=None, backend="cmake"):
    backend = (parameters or {}).get("backend") or backend
    base_cls = metac.project.get_backend_scaffolder(backend)

    custom_resources = {
      "@module@.py": reader,
      "@module@.c": None,
    } | dict(resources or {})

    params = dict(project="metac-autotest", module="autotest") | dict(parameters or {})
    return base_cls(resources=custom_resources, parameters=params)


def generate(directory=".", backend="cmake"):
  Scaffolder(backend=backend).generate(directory)

