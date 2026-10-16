import autoc.module


#
class CMake:
  
  module = None

  def __init__(self, module=None):
    if module is not None:
      self._generate(module)

  def _generate(self, module):
    cmake = f"{module.name}.cmake"
    sorted_sources = sorted(module.sources, key=lambda s: s.index)
    sources = " ".join([f"${{CMAKE_CURRENT_SOURCE_DIR}}/{s.file_name}" for s in sorted_sources])
    # A documentation-only module (source_count = 0) emits no translation units and
    # therefore declares no library - only the header the documentation is built from
    library = f"""
      add_library({module.name}-autoc OBJECT ${{{module.name}_SOURCES}})
      target_include_directories({module.name}-autoc INTERFACE $<BUILD_INTERFACE:${{CMAKE_CURRENT_SOURCE_DIR}}>)
    """ if sources else str()
    contents = f"""
      set({module.name}_HEADER ${{CMAKE_CURRENT_SOURCE_DIR}}/{module.header.file_name})
      set({module.name}_SOURCES {sources})
      set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS
        ${{{module.name}_HEADER}}
        ${{{module.name}_SOURCES}}
      ){library}
    """
    try:
      with open(cmake, "r") as f:
        if not f.read() == contents:
          raise Exception()
    except:
      with open(cmake, "w") as f:
        f.write(contents)

  def __enter__(self):
    self.__context = autoc.module._build_context
    autoc.module._build_context = self
    return self
  
  def __exit__(self, exc_type, exc_value, traceback):
    if self.module:
      self._generate(self.module)
    autoc.module._build_context = self.__context
    return False


### On code generation vs. CMake

# https://here-be-braces.com/integrating-a-flexible-code-generator-into-cmake/
# https://blog.kangz.net/posts/2016/05/26/integrating-a-code-generator-with-cmake/


### On code packaging

# https://www.youtube.com/watch?v=sBP17HQAQjk
# https://www.youtube.com/watch?v=_5weX5mx8hc

# https://alexreinking.com/blog/how-to-use-cmake-without-the-agonizing-pain-part-1.html
# https://alexreinking.com/blog/how-to-use-cmake-without-the-agonizing-pain-part-2.html


import autoc.project.cmake

Scaffolder = autoc.project.cmake.Scaffolder


