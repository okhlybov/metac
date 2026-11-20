import os
import re
import shutil
import subprocess
import tempfile
import unittest


class TestDocumentationExamples(unittest.TestCase):

  def test_readme_quick_start(self):
    readme_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "README.md"))
    self.assertTrue(os.path.exists(readme_path), f"README not found at {readme_path}")

    with open(readme_path, "r", encoding="utf-8") as f:
      content = f.read()

    # Extract Quick start section
    qs_match = re.search(r"## Quick start\s*(.*?)(?=###|\Z)", content, re.DOTALL)
    self.assertIsNotNone(qs_match, "Quick start section not found in README.md")
    qs = qs_match.group(1)

    # Extract python snippet
    py_match = re.search(r"```python\s*(.*?)\s*```", qs, re.DOTALL)
    self.assertIsNotNone(py_match, "Python code block not found in Quick start")
    py_code = py_match.group(1)

    # Extract C snippet
    c_match = re.search(r"```c\s*(.*?)\s*```", qs, re.DOTALL)
    self.assertIsNotNone(c_match, "C code block not found in Quick start")
    c_code = c_match.group(1)

    cc = os.environ.get("CC") or shutil.which("gcc") or shutil.which("clang") or shutil.which("cc")
    if not cc:
      self.skipTest("No C compiler found")

    with tempfile.TemporaryDirectory() as tmpdir:
      # Run Python generation script
      py_script = os.path.join(tmpdir, "mymodule.py")
      with open(py_script, "w", encoding="utf-8") as f:
        f.write(py_code + "\n")

      env = dict(os.environ)
      repo_src = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
      existing_pythonpath = env.get("PYTHONPATH", "")
      env["PYTHONPATH"] = f"{repo_src}:{existing_pythonpath}" if existing_pythonpath else repo_src

      proc = subprocess.run([os.sys.executable, py_script], cwd=tmpdir, env=env, capture_output=True, text=True)
      self.assertEqual(proc.returncode, 0, f"Python generator failed: {proc.stderr}")

      # Verify generated headers and sources
      h_file = os.path.join(tmpdir, "mymodule_auto.h")
      c_file = os.path.join(tmpdir, "mymodule_auto.c")
      self.assertTrue(os.path.exists(h_file), "mymodule_auto.h was not generated")
      self.assertTrue(os.path.exists(c_file), "mymodule_auto.c was not generated")

      # Build main.c wrapping the C snippet
      main_c = os.path.join(tmpdir, "main.c")
      main_content = f"""
#include <stdio.h>
#include <assert.h>
{c_code}

int main(void) {{
  /* In README the snippet is bare statements; if not inside a function, wrap them */
  return 0;
}}
"""
      # If c_code doesn't define main, wrap its statements inside main:
      if "int main(" not in c_code:
        main_content = f"""
#include <stdio.h>
#include <assert.h>
#include "mymodule_auto.h"

int main(void) {{
{c_code}
  return 0;
}}
"""
      with open(main_c, "w", encoding="utf-8") as f:
        f.write(main_content)

      out_bin = os.path.join(tmpdir, "quickstart_bin")
      compile_cmd = [cc, "-I" + tmpdir, main_c, c_file, "-o", out_bin]
      c_proc = subprocess.run(compile_cmd, cwd=tmpdir, capture_output=True, text=True)
      self.assertEqual(c_proc.returncode, 0, f"Compilation of README quick start failed:\n{c_proc.stderr}")

      run_proc = subprocess.run([out_bin], cwd=tmpdir, capture_output=True, text=True)
      self.assertEqual(run_proc.returncode, 0, f"Running README quick start binary failed:\n{run_proc.stderr}")
