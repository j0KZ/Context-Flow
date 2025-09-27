cmake_minimum_required(VERSION 3.10)
project(ContextFlow VERSION 4.0.0 LANGUAGES C CXX)

# Set C/C++ standards
set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Options
option(BUILD_SHARED_LIBS "Build shared libraries" ON)
option(BUILD_TESTS "Build tests" ON)
option(BUILD_EXAMPLES "Build examples" ON)
option(BUILD_CPP_WRAPPER "Build C++ wrapper" ON)
option(ENABLE_LTO "Enable Link Time Optimization" ON)

# Compiler flags
if(CMAKE_C_COMPILER_ID MATCHES "GNU|Clang")
    set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -Wall -Wextra -Wpedantic")
    set(CMAKE_C_FLAGS_DEBUG "${CMAKE_C_FLAGS_DEBUG} -g -O0")
    set(CMAKE_C_FLAGS_RELEASE "${CMAKE_C_FLAGS_RELEASE} -O3 -march=native")

    if(ENABLE_LTO)
        set(CMAKE_C_FLAGS_RELEASE "${CMAKE_C_FLAGS_RELEASE} -flto")
    endif()
elseif(MSVC)
    set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} /W4")
    set(CMAKE_C_FLAGS_RELEASE "${CMAKE_C_FLAGS_RELEASE} /O2")
endif()

# Include directories
include_directories(c/include)

# C Library
add_library(contextflow
    c/src/contextflow.c
)

target_include_directories(contextflow PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/c/include>
    $<INSTALL_INTERFACE:include>
)

set_target_properties(contextflow PROPERTIES
    VERSION ${PROJECT_VERSION}
    SOVERSION ${PROJECT_VERSION_MAJOR}
    PUBLIC_HEADER c/include/contextflow.h
)

# C++ Wrapper
if(BUILD_CPP_WRAPPER)
    add_library(contextflow_cpp
        cpp/src/contextflow_cpp.cpp
    )

    target_include_directories(contextflow_cpp PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/cpp/include>
        $<INSTALL_INTERFACE:include>
    )

    target_link_libraries(contextflow_cpp PUBLIC contextflow)

    set_target_properties(contextflow_cpp PROPERTIES
        VERSION ${PROJECT_VERSION}
        SOVERSION ${PROJECT_VERSION_MAJOR}
        PUBLIC_HEADER cpp/include/contextflow.hpp
    )
endif()

# Tests
if(BUILD_TESTS)
    enable_testing()

    # C tests
    add_executable(test_contextflow_c
        c/tests/test_contextflow.c
    )
    target_link_libraries(test_contextflow_c contextflow)
    add_test(NAME test_c COMMAND test_contextflow_c)

    # C++ tests
    if(BUILD_CPP_WRAPPER)
        add_executable(test_contextflow_cpp
            cpp/tests/test_contextflow_cpp.cpp
        )
        target_link_libraries(test_contextflow_cpp contextflow_cpp)
        add_test(NAME test_cpp COMMAND test_contextflow_cpp)
    endif()
endif()

# Examples
if(BUILD_EXAMPLES)
    # C example
    add_executable(example_c
        c/examples/example.c
    )
    target_link_libraries(example_c contextflow)

    # C++ example
    if(BUILD_CPP_WRAPPER)
        add_executable(example_cpp
            cpp/examples/example.cpp
        )
        target_link_libraries(example_cpp contextflow_cpp)
    endif()
endif()

# Installation
include(GNUInstallDirs)

install(TARGETS contextflow
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
    PUBLIC_HEADER DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}
)

if(BUILD_CPP_WRAPPER)
    install(TARGETS contextflow_cpp
        LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
        ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
        RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
        PUBLIC_HEADER DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}
    )
endif()

# Package configuration
include(CMakePackageConfigHelpers)

write_basic_package_version_file(
    "${CMAKE_CURRENT_BINARY_DIR}/ContextFlowConfigVersion.cmake"
    VERSION ${PROJECT_VERSION}
    COMPATIBILITY AnyNewerVersion
)

configure_package_config_file(
    "${CMAKE_CURRENT_SOURCE_DIR}/cmake/ContextFlowConfig.cmake.in"
    "${CMAKE_CURRENT_BINARY_DIR}/ContextFlowConfig.cmake"
    INSTALL_DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/ContextFlow
)

install(FILES
    "${CMAKE_CURRENT_BINARY_DIR}/ContextFlowConfig.cmake"
    "${CMAKE_CURRENT_BINARY_DIR}/ContextFlowConfigVersion.cmake"
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/ContextFlow
)

# Export targets
install(EXPORT ContextFlowTargets
    FILE ContextFlowTargets.cmake
    NAMESPACE ContextFlow::
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/ContextFlow
)

# CPack configuration
set(CPACK_PACKAGE_VERSION_MAJOR ${PROJECT_VERSION_MAJOR})
set(CPACK_PACKAGE_VERSION_MINOR ${PROJECT_VERSION_MINOR})
set(CPACK_PACKAGE_VERSION_PATCH ${PROJECT_VERSION_PATCH})
set(CPACK_PACKAGE_DESCRIPTION_SUMMARY "High-performance compression library with KB-scale memory")
set(CPACK_PACKAGE_VENDOR "ContextFlow")
set(CPACK_RESOURCE_FILE_LICENSE "${CMAKE_CURRENT_SOURCE_DIR}/../LICENSE")
set(CPACK_RESOURCE_FILE_README "${CMAKE_CURRENT_SOURCE_DIR}/../README.md")

include(CPack)