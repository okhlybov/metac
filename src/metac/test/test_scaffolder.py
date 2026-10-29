import os
import tempfile
import pathlib
from metac.scaffolder import Scaffolder
import metac.sample


def test_seeding_creates_metacignore():
  with tempfile.TemporaryDirectory() as tmpdir:
    metac.sample.generate(directory=tmpdir, project="demo", backend="cmake")
    metacignore_path = os.path.join(tmpdir, ".metacignore")
    assert os.path.exists(metacignore_path), ".metacignore was not created during seeding"
    with open(metacignore_path, "r", encoding="utf-8") as f:
      content = f.read()
    assert content == "demo.py\ndemo.c\n", f"Unexpected .metacignore content: {repr(content)}"


def test_upgrade_preserves_ignored_and_refreshes_scaffolding():
  with tempfile.TemporaryDirectory() as tmpdir:
    metac.sample.generate(directory=tmpdir, project="demo", backend="cmake")
    
    # User edits their source code
    demo_py = os.path.join(tmpdir, "demo.py")
    demo_c = os.path.join(tmpdir, "demo.c")
    with open(demo_py, "w", encoding="utf-8") as f:
      f.write("# user customized demo.py")
    with open(demo_c, "w", encoding="utf-8") as f:
      f.write("// user customized demo.c")

    # Tamper with a scaffolding file (e.g. CMakeLists.txt)
    cmakelists = os.path.join(tmpdir, "CMakeLists.txt")
    with open(cmakelists, "w", encoding="utf-8") as f:
      f.write("# outdated scaffolding")

    # Perform upgrade
    metac.sample.generate(directory=tmpdir, project="demo", backend="cmake", upgrade=True)

    # User files must be preserved
    with open(demo_py, "r", encoding="utf-8") as f:
      assert f.read() == "# user customized demo.py"
    with open(demo_c, "r", encoding="utf-8") as f:
      assert f.read() == "// user customized demo.c"

    # Scaffolding file must be refreshed
    with open(cmakelists, "r", encoding="utf-8") as f:
      refreshed = f.read()
    assert refreshed != "# outdated scaffolding"
    assert "project(demo C)" in refreshed or "cmake_minimum_required" in refreshed


def test_upgrade_missing_metacignore_raises_error():
  with tempfile.TemporaryDirectory() as tmpdir:
    metac.sample.generate(directory=tmpdir, project="demo", backend="cmake")
    
    # Remove .metacignore to simulate incomplete checkout
    metacignore_path = os.path.join(tmpdir, ".metacignore")
    os.remove(metacignore_path)

    error_raised = False
    try:
      metac.sample.generate(directory=tmpdir, project="demo", backend="cmake", upgrade=True)
    except FileNotFoundError as e:
      error_raised = True
      assert ".metacignore" in str(e)
    assert error_raised, "Expected FileNotFoundError when upgrading with missing .metacignore"


def test_custom_tailored_metacignore():
  with tempfile.TemporaryDirectory() as tmpdir:
    metac.sample.generate(directory=tmpdir, project="demo", backend="cmake")

    # User appends custom non-upgradeable files to .metacignore
    metacignore_path = os.path.join(tmpdir, ".metacignore")
    with open(metacignore_path, "a", encoding="utf-8") as f:
      f.write("\n# Additional user rules\nCMakePresets.json\ncmake/*\n")

    presets_path = os.path.join(tmpdir, "CMakePresets.json")
    with open(presets_path, "w", encoding="utf-8") as f:
      f.write('{"custom": true}')

    metac_cmake = os.path.join(tmpdir, "cmake", "MetaC.cmake")
    with open(metac_cmake, "w", encoding="utf-8") as f:
      f.write("# custom cmake helper")

    # Upgrade
    metac.sample.generate(directory=tmpdir, project="demo", backend="cmake", upgrade=True)

    # Tailored files must be preserved
    with open(presets_path, "r", encoding="utf-8") as f:
      assert f.read() == '{"custom": true}'
    with open(metac_cmake, "r", encoding="utf-8") as f:
      assert f.read() == "# custom cmake helper"


def test_metacignore_negation_rules():
  with tempfile.TemporaryDirectory() as tmpdir:
    metac.sample.generate(directory=tmpdir, project="demo", backend="cmake")

    # Ignore all json except CMakePresets.json
    metacignore_path = os.path.join(tmpdir, ".metacignore")
    with open(metacignore_path, "w", encoding="utf-8") as f:
      f.write("demo.py\ndemo.c\n*.json\n!CMakePresets.json\n")

    launch_json = os.path.join(tmpdir, ".vscode", "launch.json")
    with open(launch_json, "w", encoding="utf-8") as f:
      f.write('{"custom_launch": true}')

    presets_path = os.path.join(tmpdir, "CMakePresets.json")
    with open(presets_path, "w", encoding="utf-8") as f:
      f.write('{"outdated": true}')

    # Upgrade
    metac.sample.generate(directory=tmpdir, project="demo", backend="cmake", upgrade=True)

    # .vscode/launch.json matched *.json and was not un-ignored -> preserved
    with open(launch_json, "r", encoding="utf-8") as f:
      assert f.read() == '{"custom_launch": true}'

    # CMakePresets.json was negated by !CMakePresets.json -> refreshed!
    with open(presets_path, "r", encoding="utf-8") as f:
      assert f.read() != '{"outdated": true}'


def test_seeding_preserves_existing_metacignore():
  with tempfile.TemporaryDirectory() as tmpdir:
    metacignore_path = os.path.join(tmpdir, ".metacignore")
    with open(metacignore_path, "w", encoding="utf-8") as f:
      f.write("# existing custom content\ncustom.py\n")

    # Re-run seeding (not upgrade)
    metac.sample.generate(directory=tmpdir, project="demo", backend="cmake")

    with open(metacignore_path, "r", encoding="utf-8") as f:
      assert f.read() == "# existing custom content\ncustom.py\n"


def test_backend_scaffolders():
  for backend in ("meson", "scons"):
    with tempfile.TemporaryDirectory() as tmpdir:
      metac.sample.generate(directory=tmpdir, project="testproj", backend=backend)
      metacignore_path = os.path.join(tmpdir, ".metacignore")
      assert os.path.exists(metacignore_path), f".metacignore not created for {backend}"
      with open(metacignore_path, "r", encoding="utf-8") as f:
        assert f.read() == "testproj.py\ntestproj.c\n"

      # Upgrade works cleanly
      metac.sample.generate(directory=tmpdir, project="testproj", backend=backend, upgrade=True)


if __name__ == "__main__":
  test_seeding_creates_metacignore()
  test_upgrade_preserves_ignored_and_refreshes_scaffolding()
  test_upgrade_missing_metacignore_raises_error()
  test_custom_tailored_metacignore()
  test_metacignore_negation_rules()
  test_seeding_preserves_existing_metacignore()
  test_backend_scaffolders()
  print("All scaffolder tests passed!")
