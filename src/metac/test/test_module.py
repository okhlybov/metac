import os
import re
import glob
import time
import tempfile
from metac.module import Module, Source, Code


# Test 1: Split -> Fewer split (5 -> 2)
with tempfile.TemporaryDirectory() as tmpdir:
  prefix = os.path.join(tmpdir, "m")
  with Module(prefix, source_count=5, stateful=False) as m:
    for i in range(5):
      m.add(Code(definitions=f"int var_{i} = {i};"))
  initial_files = sorted(os.listdir(tmpdir))
  assert initial_files == ["m_auto.h", "m_auto1.c", "m_auto2.c", "m_auto3.c", "m_auto4.c", "m_auto5.c"]

  with Module(prefix, source_count=2, stateful=False) as m:
    m.add(Code(definitions="int var_0 = 0;"))
    m.add(Code(definitions="int var_1 = 1;"))
  after_files = sorted(os.listdir(tmpdir))
  assert after_files == ["m_auto.h", "m_auto1.c", "m_auto2.c"], f"Expected [m_auto.h, m_auto1.c, m_auto2.c], got {after_files}"

# Test 2: Split -> Single (3 -> 1)
with tempfile.TemporaryDirectory() as tmpdir:
  prefix = os.path.join(tmpdir, "m")
  with Module(prefix, source_count=3, stateful=False) as m:
    for i in range(3):
      m.add(Code(definitions=f"int x_{i} = {i};"))
  assert sorted(os.listdir(tmpdir)) == ["m_auto.h", "m_auto1.c", "m_auto2.c", "m_auto3.c"]

  with Module(prefix, source_count=1, stateful=False) as m:
    m.add(Code(definitions="int x = 1;"))
  assert sorted(os.listdir(tmpdir)) == ["m_auto.c", "m_auto.h"]

# Test 3: Single -> Split (1 -> 3)
with tempfile.TemporaryDirectory() as tmpdir:
  prefix = os.path.join(tmpdir, "m")
  with Module(prefix, source_count=1, stateful=False) as m:
    m.add(Code(definitions="int x = 1;"))
  assert sorted(os.listdir(tmpdir)) == ["m_auto.c", "m_auto.h"]

  with Module(prefix, source_count=3, stateful=False) as m:
    for i in range(3):
      m.add(Code(definitions=f"int y_{i} = {i};"))
  assert sorted(os.listdir(tmpdir)) == ["m_auto.h", "m_auto1.c", "m_auto2.c", "m_auto3.c"]

# Test 4: Disable sources (3 -> 0)
with tempfile.TemporaryDirectory() as tmpdir:
  prefix = os.path.join(tmpdir, "m")
  with Module(prefix, source_count=3, stateful=False) as m:
    for i in range(3):
      m.add(Code(definitions=f"int z_{i} = {i};"))
  assert sorted(os.listdir(tmpdir)) == ["m_auto.h", "m_auto1.c", "m_auto2.c", "m_auto3.c"]

  with Module(prefix, source_count=0, stateful=False) as m:
    m.add(Code(definitions="int z = 0;"))
  assert sorted(os.listdir(tmpdir)) == ["m_auto.h"]

# Test 5: Unrelated and similarly-named files are preserved
with tempfile.TemporaryDirectory() as tmpdir:
  prefix = os.path.join(tmpdir, "m")
  protected_files = [
    "m_auto.h",
    "m_auto_backup.c~",
    "m_auto_backup.c",
    "m_auto_extra.c",
    "m_automatic.c",
    "m_automotive.c",
    "other_auto1.c",
    "m_auto.o"
  ]
  for f in protected_files:
    with open(os.path.join(tmpdir, f), "w") as fp:
      fp.write("// keep me")

  with Module(prefix, source_count=2, stateful=False) as m:
    m.add(Code(definitions="int a = 1;"))
    m.add(Code(definitions="int b = 2;"))

  current_files = set(os.listdir(tmpdir))
  for f in protected_files:
    assert f in current_files, f"Protected file {f} was mistakenly deleted!"
  assert "m_auto1.c" in current_files and "m_auto2.c" in current_files

  with Module(prefix, source_count=1, stateful=False) as m:
    m.add(Code(definitions="int a = 1;"))

  current_files = set(os.listdir(tmpdir))
  for f in protected_files:
    assert f in current_files, f"Protected file {f} was mistakenly deleted!"
  assert "m_auto.c" in current_files
  assert "m_auto1.c" not in current_files
  assert "m_auto2.c" not in current_files

# Test 6: Gaps in stray file indices
with tempfile.TemporaryDirectory() as tmpdir:
  prefix = os.path.join(tmpdir, "m")
  with Module(prefix, source_count=4, stateful=False) as m:
    for i in range(4):
      m.add(Code(definitions=f"int a_{i} = {i};"))
  os.unlink(os.path.join(tmpdir, "m_auto2.c"))

  with Module(prefix, source_count=1, stateful=False) as m:
    m.add(Code(definitions="int a = 1;"))

  files = sorted(os.listdir(tmpdir))
  assert files == ["m_auto.c", "m_auto.h"], f"Expected [m_auto.c, m_auto.h], got {files}"

# Test 7: Nested directories / relative paths
with tempfile.TemporaryDirectory() as tmpdir:
  subdir = os.path.join(tmpdir, "sub", "dir")
  os.makedirs(subdir)
  prefix = os.path.join(subdir, "nested")
  with Module(prefix, source_count=3, stateful=False) as m:
    for i in range(3):
      m.add(Code(definitions=f"int n_{i} = {i};"))
  assert sorted(os.listdir(subdir)) == ["nested_auto.h", "nested_auto1.c", "nested_auto2.c", "nested_auto3.c"]

  with Module(prefix, source_count=1, stateful=False) as m:
    m.add(Code(definitions="int n = 0;"))
  assert sorted(os.listdir(subdir)) == ["nested_auto.c", "nested_auto.h"]

# Test 8: Stateful mode with .state file
with tempfile.TemporaryDirectory() as tmpdir:
  prefix = os.path.join(tmpdir, "m")
  with Module(prefix, source_count=3, stateful=True) as m:
    for i in range(3):
      m.add(Code(definitions=f"int s_{i} = {i};"))
  assert sorted(os.listdir(tmpdir)) == [".metac", "m_auto.h", "m_auto1.c", "m_auto2.c", "m_auto3.c"]
  assert os.path.exists(os.path.join(tmpdir, ".metac", "m.state"))

  with Module(prefix, source_count=1, stateful=True) as m:
    m.add(Code(definitions="int s = 0;"))
  assert sorted(os.listdir(tmpdir)) == [".metac", "m_auto.c", "m_auto.h"]
  with open(os.path.join(tmpdir, ".metac", "m.state")) as fp:
    state_content = fp.read()
  assert "m_auto1.c" not in state_content
  assert "m_auto.c" in state_content

# Test 9: Custom Source subclass
class CustomSource(Source):
  @classmethod
  def _generate_file_name(cls, prefix, index, count):
    return f"{prefix}_custom{index}.c" if count > 1 else f"{prefix}_custom.c"

with tempfile.TemporaryDirectory() as tmpdir:
  prefix = os.path.join(tmpdir, "m")
  with Module(prefix, source=CustomSource, source_count=3, stateful=False) as m:
    for i in range(3):
      m.add(Code(definitions=f"int c_{i} = {i};"))
  assert sorted(os.listdir(tmpdir)) == ["m_auto.h", "m_custom1.c", "m_custom2.c", "m_custom3.c"]

  with Module(prefix, source=CustomSource, source_count=1, stateful=False) as m:
    m.add(Code(definitions="int c = 0;"))
  assert sorted(os.listdir(tmpdir)) == ["m_auto.h", "m_custom.c"]

# Test 10: Stateless idempotency (stateful=False preserves timestamps on unchanged re-runs)
with tempfile.TemporaryDirectory() as tmpdir:
  prefix = os.path.join(tmpdir, "m")
  with Module(prefix, stateful=False) as m:
    m.add(Code(definitions="int a = 1;"))
  h_path = os.path.join(tmpdir, "m_auto.h")
  c_path = os.path.join(tmpdir, "m_auto.c")
  h_mtime1 = os.path.getmtime(h_path)
  c_mtime1 = os.path.getmtime(c_path)

  time.sleep(0.05)

  with Module(prefix, stateful=False) as m:
    m.add(Code(definitions="int a = 1;"))
  h_mtime2 = os.path.getmtime(h_path)
  c_mtime2 = os.path.getmtime(c_path)

  assert h_mtime1 == h_mtime2, "Header was unnecessarily overwritten in stateless mode!"
  assert c_mtime1 == c_mtime2, "Source was unnecessarily overwritten in stateless mode!"
  assert not os.path.exists(os.path.join(tmpdir, ".metac", "m.state"))

# Test 11: Switch from stateful to stateless removes stray .state file
with tempfile.TemporaryDirectory() as tmpdir:
  prefix = os.path.join(tmpdir, "m")
  with Module(prefix, stateful=True) as m:
    m.add(Code(definitions="int a = 1;"))
  state_path = os.path.join(tmpdir, ".metac", "m.state")
  assert os.path.exists(state_path)

  with Module(prefix, stateful=False) as m:
    m.add(Code(definitions="int a = 1;"))
  assert not os.path.exists(state_path), "Stray .state file was not removed when switched to stateful=False!"

