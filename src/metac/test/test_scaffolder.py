import os
import sys
import subprocess
import tempfile
import pathlib
from metac.scaffolder import Scaffolder
import metac.sample
import metac.test
import metac.autotest
import metac.doc


def test_seeding_creates_metacignore():
  with tempfile.TemporaryDirectory() as tmpdir:
    rc = metac.sample.generate(directory=tmpdir, project="demo", backend="cmake")
    assert rc == 0
    metacignore_path = os.path.join(tmpdir, ".metacignore")
    assert os.path.exists(metacignore_path), ".metacignore was not created during seeding"
    with open(metacignore_path, "r", encoding="utf-8") as f:
      content = f.read()
    assert content == "demo.py\ndemo.c\n", f"Unexpected .metacignore content: {repr(content)}"


def test_seeding_specialized_scaffolders():
  for mod, expected_file in [
    (metac.test, "test.py\n"),
    (metac.autotest, "autotest.py\n"),
    (metac.doc, "doc.py\n"),
  ]:
    with tempfile.TemporaryDirectory() as tmpdir:
      rc = mod.generate(directory=tmpdir, backend="cmake")
      assert rc == 0
      metacignore_path = os.path.join(tmpdir, ".metacignore")
      assert os.path.exists(metacignore_path), f".metacignore not created for {mod.__name__}"
      with open(metacignore_path, "r", encoding="utf-8") as f:
        content = f.read()
      assert content == expected_file, f"Expected {repr(expected_file)}, got {repr(content)}"


def test_seeding_refuses_to_overwrite_without_force():
  with tempfile.TemporaryDirectory() as tmpdir:
    # First seed succeeds
    rc1 = metac.sample.generate(directory=tmpdir, project="demo", backend="cmake")
    assert rc1 == 0

    # User modifies demo.py
    demo_py = os.path.join(tmpdir, "demo.py")
    with open(demo_py, "w", encoding="utf-8") as f:
      f.write("# user code")

    # Second seed without force must return non-zero (1) and refuse to overwrite
    rc2 = metac.sample.generate(directory=tmpdir, project="demo", backend="cmake")
    assert rc2 != 0, "Seeding without force into existing files should fail with non-zero code"

    # User file was preserved
    with open(demo_py, "r", encoding="utf-8") as f:
      assert f.read() == "# user code"


def test_seeding_overwrites_with_force():
  with tempfile.TemporaryDirectory() as tmpdir:
    # First seed
    rc1 = metac.sample.generate(directory=tmpdir, project="demo", backend="cmake")
    assert rc1 == 0

    demo_py = os.path.join(tmpdir, "demo.py")
    with open(demo_py, "w", encoding="utf-8") as f:
      f.write("# user code")

    # Second seed with force=True must succeed (return 0) and overwrite
    rc2 = metac.sample.generate(directory=tmpdir, project="demo", backend="cmake", force=True)
    assert rc2 == 0

    with open(demo_py, "r", encoding="utf-8") as f:
      assert f.read() != "# user code"


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
    rc = metac.sample.generate(directory=tmpdir, project="demo", backend="cmake", upgrade=True)
    assert rc == 0

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


def test_upgrade_missing_metacignore_returns_nonzero_without_exception():
  with tempfile.TemporaryDirectory() as tmpdir:
    metac.sample.generate(directory=tmpdir, project="demo", backend="cmake")
    
    # Remove .metacignore to simulate incomplete checkout
    metacignore_path = os.path.join(tmpdir, ".metacignore")
    os.remove(metacignore_path)

    # Must return non-zero and not raise an unhandled exception
    rc = metac.sample.generate(directory=tmpdir, project="demo", backend="cmake", upgrade=True)
    assert rc != 0, "Expected non-zero return code when upgrading with missing .metacignore"


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
    rc = metac.sample.generate(directory=tmpdir, project="demo", backend="cmake", upgrade=True)
    assert rc == 0

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
    rc = metac.sample.generate(directory=tmpdir, project="demo", backend="cmake", upgrade=True)
    assert rc == 0

    # .vscode/launch.json matched *.json and was not un-ignored -> preserved
    with open(launch_json, "r", encoding="utf-8") as f:
      assert f.read() == '{"custom_launch": true}'

    # CMakePresets.json was negated by !CMakePresets.json -> refreshed!
    with open(presets_path, "r", encoding="utf-8") as f:
      assert f.read() != '{"outdated": true}'


def test_backend_scaffolders():
  for backend in ("meson", "scons"):
    with tempfile.TemporaryDirectory() as tmpdir:
      rc1 = metac.sample.generate(directory=tmpdir, project="testproj", backend=backend)
      assert rc1 == 0
      metacignore_path = os.path.join(tmpdir, ".metacignore")
      assert os.path.exists(metacignore_path), f".metacignore not created for {backend}"
      with open(metacignore_path, "r", encoding="utf-8") as f:
        assert f.read() == "testproj.py\ntestproj.c\n"

      # Re-seeding without force must fail
      rc_fail = metac.sample.generate(directory=tmpdir, project="testproj", backend=backend)
      assert rc_fail != 0

      # Upgrade works cleanly
      rc_up = metac.sample.generate(directory=tmpdir, project="testproj", backend=backend, upgrade=True)
      assert rc_up == 0



def test_cli_factored_helper():
  from metac.scaffolder import cli

  called_args = {}
  def dummy_gen(**kwargs):
    called_args.update(kwargs)
    return 0

  # Default options
  rc = cli(dummy_gen, description="Test generator", args=["my_dir"], exit=False)
  assert rc == 0
  assert called_args == {"directory": "my_dir", "upgrade": False, "force": False, "project": None, "backend": "cmake"}

  # With meson backend default and project
  called_args.clear()
  rc = cli(dummy_gen, description="Test generator", backend="meson", args=["my_dir", "-p", "proj_x", "-u", "-f"], exit=False)
  assert rc == 0
  assert called_args == {"directory": "my_dir", "upgrade": True, "force": True, "project": "proj_x", "backend": "meson"}

  # With project=False and backend=False
  called_args.clear()
  rc = cli(dummy_gen, description="Test generator", project=False, backend=False, args=["my_dir", "-f"], exit=False)
  assert rc == 0
  assert called_args == {"directory": "my_dir", "upgrade": False, "force": True}


def test_cli_exit_codes():
  with tempfile.TemporaryDirectory() as tmpdir:
    env = os.environ.copy()
    repo_src = str(pathlib.Path(__file__).resolve().parent.parent.parent)
    env["PYTHONPATH"] = repo_src + os.pathsep + env.get("PYTHONPATH", "")

    # Seeding succeeds with exit code 0
    res = subprocess.run([sys.executable, "-m", "metac.cmake", tmpdir], env=env, capture_output=True, text=True)
    assert res.returncode == 0, f"CLI seed failed: {res.stderr}"

    # Re-seeding without --force returns non-zero code 1
    res2 = subprocess.run([sys.executable, "-m", "metac.cmake", tmpdir], env=env, capture_output=True, text=True)
    assert res2.returncode != 0, "CLI seed without force should fail"
    assert "error: Refusing to overwrite" in res2.stderr
    assert "Traceback" not in res2.stderr

    # Re-seeding with --force returns 0
    res3 = subprocess.run([sys.executable, "-m", "metac.cmake", tmpdir, "-f"], env=env, capture_output=True, text=True)
    assert res3.returncode == 0, f"CLI seed with force failed: {res3.stderr}"

    # Upgrade succeeds with exit code 0
    res4 = subprocess.run([sys.executable, "-m", "metac.cmake", tmpdir, "-u"], env=env, capture_output=True, text=True)
    assert res4.returncode == 0, f"CLI upgrade failed: {res4.stderr}"

    # Upgrade without .metacignore fails with non-zero code and error message (no traceback)
    os.remove(os.path.join(tmpdir, ".metacignore"))
    res5 = subprocess.run([sys.executable, "-m", "metac.cmake", tmpdir, "-u"], env=env, capture_output=True, text=True)
    assert res5.returncode != 0, "CLI upgrade without .metacignore should fail"
    assert "error: Missing required '.metacignore'" in res5.stderr
    assert "Traceback" not in res5.stderr


if __name__ == "__main__":
  test_seeding_creates_metacignore()
  test_seeding_specialized_scaffolders()
  test_seeding_refuses_to_overwrite_without_force()
  test_seeding_overwrites_with_force()
  test_upgrade_preserves_ignored_and_refreshes_scaffolding()
  test_upgrade_missing_metacignore_returns_nonzero_without_exception()
  test_custom_tailored_metacignore()
  test_metacignore_negation_rules()
  test_backend_scaffolders()
  test_cli_factored_helper()
  test_cli_exit_codes()
  print("All scaffolder tests passed!")
