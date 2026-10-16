cmake_minimum_required(VERSION 3.21)

project(@project@)

set(AUTOC_MODULE_NAME @module@)
set(AUTOC_MODULE_SOURCE ${CMAKE_CURRENT_SOURCE_DIR}/${AUTOC_MODULE_NAME}.py)

list(APPEND CMAKE_MODULE_PATH ${CMAKE_CURRENT_LIST_DIR}/cmake)

include(AutoC)

add_autoc_module(
  ${AUTOC_MODULE_NAME}
  DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
  MAIN_DEPENDENCY ${AUTOC_MODULE_SOURCE}
  COMMAND ${Python_EXECUTABLE} ${AUTOC_MODULE_SOURCE} ${AUTOC_MODULE_NAME}
)

if(EXISTS ${CMAKE_CURRENT_SOURCE_DIR}/${PROJECT_NAME}.c)
  add_executable(${PROJECT_NAME} ${PROJECT_NAME}.c)
  target_link_libraries(${PROJECT_NAME} ${AUTOC_MODULE_NAME}-autoc)
  enable_testing()
  add_test(NAME ${PROJECT_NAME} COMMAND ${PROJECT_NAME})
elseif(TARGET ${AUTOC_MODULE_NAME}-autoc)
  add_executable(${PROJECT_NAME})
  target_link_libraries(${PROJECT_NAME} ${AUTOC_MODULE_NAME}-autoc)
  enable_testing()
  add_test(NAME ${PROJECT_NAME} COMMAND ${PROJECT_NAME})
endif()

find_package(Doxygen)
if(Doxygen_FOUND AND EXISTS ${CMAKE_CURRENT_SOURCE_DIR}/Doxyfile)
  add_custom_target(doc
    COMMAND ${DOXYGEN_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/Doxyfile
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    COMMENT "Generating documentation with Doxygen"
    VERBATIM
  )
  if(NOT TARGET generate)
    add_custom_target(generate DEPENDS doc)
  endif()
  if(NOT TARGET ${PROJECT_NAME})
    add_custom_target(${PROJECT_NAME} DEPENDS doc)
  endif()
endif()