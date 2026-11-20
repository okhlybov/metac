# Backend-dispatching module scripts

## Goal

Make the scaffolded user module script (`@module@.py`) build-system agnostic: the build backend is resolved at generation time as **command line → `METAC_BACKEND` env var → fallback to the backend the project was first scaffolded with** (baked into the script as the default at scaffold time). All detection/dispatch code lives in the metac library so templates stay a one-line change.

## Library (metac package)

**1. New module `src/metac/backend.py`** with two functions:
- `parse(argv=None)` — scans argv for `-b NAME` / `-bNAME` / `--backend NAME` / `--backend=NAME` (consuming flag values so later positional scanning is safe), and returns `(backend_or_None, module_name_or_None, stamp_or_None)` where module name = first non-flag token after the program, stamp = second (this makes the Meson stamp detection flag-safe).
- `builder(default="cmake", argv=None)` — resolves the backend: parsed argv value, else `os.environ["METAC_BACKEND"]`, else `default`; validates against a `{"cmake", "meson", "scons"}` registry; lazily imports `metac.cmake.CMake` / `metac.meson.Meson` / `metac.scons.SCons` and returns a constructed context instance (stamp forwarded to `Meson`). Unknown backend raises `ValueError` listing valid names.

**2. `src/metac/__init__.py`** — re-export `builder` as `metac.builder` (module-level import is cheap: `backend.py` imports only `os`/`sys` at top level).

**3. `src/metac/meson/__init__.py`** — replace the raw `sys.argv[2].startswith("-")` stamp pickup in `Meson._generate` with `parse()`'s stamp, so `python script.py runme --backend=meson <stamp>` finds the stamp correctly.

## Scaffolders

**4. Per-backend project scaffolders** (`src/metac/project/{cmake,meson,scons}/__init__.py`) — each adds its `backend="<name>"` to the template parameters (alongside the existing `generator=`), so the fallback bakes into the generated script as `@backend@`.

## Templates

**5. Module script templates** — `sample`, `test`, `autotest`, and `doc` `template/@module@.py`: replace `import @generator_module@` + `with @generator@():` with `import metac` + `with metac.builder("@backend@"):`.

**6. Build file templates** — each passes its identity on the generator command line:
- `project/cmake/template/CMakeLists.txt`: `COMMAND ... ${METAC_MODULE_NAME} --backend=cmake`; same appended to the default `key_COMMAND` in `project/cmake/template/cmake/MetaC.cmake`.
- `project/meson/template/meson.build`: `--backend=meson` appended in both the bootstrap `run_command(...)` and the incremental `gen_cmd` (before the stamp argument).
- `project/scons/template/site_scons/site_tools/metac.py`: default `command` gains `"--backend=scons"`.

## The runme project (live verification target)

**7.** `runme/runme.py` switches to `with metac.builder("cmake"):`; `runme/CMakeLists.txt` explicit `COMMAND` line gains `--backend=cmake`. This turns runme into the working multi-backend hybrid that currently fails to build.

## Verification

1. Fresh-scaffold sample projects per backend into /tmp; configure+build all three backends — green.
2. The regression case: scaffold a cmake project, layer meson and scons wiring on top (today's runme scenario), build all three — green.
3. runme: cmake still builds; meson and scons now bootstrap and build (previously both failed).
4. `METAC_BACKEND=meson` on a cmake-flagged invocation produces `runme.meson` (env resolution proven); bare `python runme.py runme` produces `runme.cmake` (fallback proven).
5. Regenerate + build the metac test and autotest suites (they consume the changed templates) — all tests pass.
6. Meson incremental regen (touch `runme.py`, ninja) still stamps correctly with the flag in argv.