# Tutorial: a complete project, end to end {#tutorial}

Let's build a small but real program — a sensor log that accumulates readings into a
**list of ints**, aggregates them and drains them — from an empty directory to a running
binary.

## 1. Install the generator

From a checkout of this repository (Python ≥ 3.10 required):

```sh
pip install .
```

(During development, `pip install -e .` and `PYTHONPATH=src` both work.)

> **Tip:** You can also scaffold a ready-to-run project automatically for CMake, SCons, or Meson:
> ```sh
> python -m metac.cmake sensors   # replace cmake with meson, scons
> cd sensors
> ```

## 2. Define the module

Create `sensors.py`:

```python
import sys
import metac.module
import metac.list
import metac.cmake

with metac.cmake.CMake():
  with metac.module.Module("sensors") as m:
    m.add(metac.list.List("int_list", "int"))
```

`List("int_list", "int")` asks for one concrete container: a singly linked list whose
elements are `int`, spelled `int_list` in C. Nothing is generic at run time — the generator
writes a fully specialized list.

## 3. Generate

```sh
python3 sensors.py
```

This produces:

- `sensors_auto.h` — the interface: the `int_list` type, the `int_list_range` type and the
  function declarations;
- `sensors_auto.c` — the implementations;
- `sensors.cmake` — CMake glue declaring the `sensors-auto` library.

Open `sensors_auto.h`. Every operation you need is declared there, and the brief comment
above each one tells you what it does. The list itself is opaque: its representation lives
in the header but is marked `@private` — you are expected to drive it through the functions.

## 4. CMake integration

The generated `sensors.cmake` is included by the project module found in `cmake/MetaC.cmake`,
which also provides `add_metac_module()`:

```cmake
cmake_minimum_required(VERSION 3.21)
project(sensors)

list(APPEND CMAKE_MODULE_PATH ${CMAKE_CURRENT_LIST_DIR}/cmake)
include(MetaC)

add_metac_module(
  sensors
  DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
  MAIN_DEPENDENCY ${CMAKE_CURRENT_SOURCE_DIR}/sensors.py
  COMMAND ${Python_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/sensors.py
)

add_executable(sensors sensors.c)
target_link_libraries(sensors sensors-auto)
```

`add_metac_module()` bootstraps the generation on the first configure and re-runs the
generator whenever `sensors.py` (or its declared dependencies) change. Execution is
tracked by a state file, so the code is regenerated only when the definitions actually
change. Equivalent integration is provided for SCons (via `env.MetaCModule()`) and Meson
(via `custom_target()`).

If you prefer to stay with plain `make`/`cc` for now, just compile `sensors.c` together with
`sensors_auto.c` and add `-I.` to the include path.

## 5. Write the program

Create `sensors.c`:

```c
#include <stdio.h>
#include "sensors_auto.h"

int main(void) {
  int_list readings;
  int_list_range r;
  int total = 0, count = 0;

  int_list_create(&readings);
  int_list_push_front(&readings, 20);
  int_list_push_front(&readings, 25);
  int_list_push_front(&readings, 15);

  for(r = int_list_range_new(&readings); !int_list_range_empty(&r);
      int_list_range_move_front(&r)) {
    total += int_list_range_front(&r);
    ++count;
  }

  printf("%d reading(s), average %d\n", count, count ? total / count : 0);

  /* drain */
  while(!int_list_empty(&readings)) {
    int value = int_list_pop_front(&readings);
    printf("drained %d\n", value);
  }

  int_list_destroy(&readings);
  return 0;
}
```

A few things are worth noticing:

- **Construction is explicit.** `int_list_create()` puts the list into a valid empty state;
  `int_list_destroy()` releases everything. There is no hidden initialization.
- **Ranges are value types.** `int_list_range_new(&readings)` returns a cursor by value; the
  cursor does not own anything and does not keep the container alive. `move_front` advances
  it. Because the range is a value, you can copy it (`int_list_range_copy`) and keep a second
  traversal position.
- **The element accessors come in two flavours.** `front` returns a *copy* of the element
  (`int` here, so it is cheap); `front_view` returns a `const int*` borrowed from inside the
  container, valid until the container is modified or destroyed.

## 6. Build and run

```sh
cmake -S . -B build/debug -DCMAKE_BUILD_TYPE=Debug
cmake --build build/debug
./build/debug/sensors
```

Expected output:

```
3 reading(s), average 20
drained 15
drained 25
drained 20
```

## 7. Next steps

- Swap `metac.list.List` for `metac.vector.Vector` (direct access, cache friendly) and the
  program keeps working with two changes: the type name and the header. The operations you
  already use — `create`, `destroy`, `push_front`, `pop_front`, `empty`, `size` — are spelled
  the same.
- Add a second container to the same module and it shares the same header, its own range and
  its own group of functions.
- Read @ref design to understand the value-semantics protocol every type implements, and
  @ref containers to choose the container that fits your access pattern.