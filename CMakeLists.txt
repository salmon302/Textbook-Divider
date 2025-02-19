cmake_minimum_required(VERSION 3.28)
project(Textbook_Divider)

set(CMAKE_CXX_STANDARD 20)

# Add cmake modules path
list(APPEND CMAKE_MODULE_PATH ${CMAKE_SOURCE_DIR}/cmake)

# Find required packages
find_package(OpenGL REQUIRED)
find_package(glfw3 REQUIRED)
find_package(PoDoFo REQUIRED)

# Find Java and JNI
find_package(Java REQUIRED)
find_package(JNI REQUIRED)

# Set Audiveris paths
set(AUDIVERIS_DIR ${CMAKE_SOURCE_DIR}/external/audiveris)
set(AUDIVERIS_JAR ${AUDIVERIS_DIR}/build/jar/audiveris.jar)

# Set Python executable to use virtual environment
set(Python3_EXECUTABLE "${CMAKE_SOURCE_DIR}/venv/bin/python3")
set(Python3_FIND_VIRTUALENV FIRST)

# Find Python with virtual environment
find_package(Python3 COMPONENTS Interpreter Development REQUIRED)

# Add site-packages to runtime environment
set(PYTHON_SITE_PACKAGES "${CMAKE_SOURCE_DIR}/venv/lib/python3.12/site-packages")
execute_process(
    COMMAND "${Python3_EXECUTABLE}" -c "import numpy; print(numpy.get_include())"
    OUTPUT_VARIABLE NumPy_INCLUDE_DIR
    OUTPUT_STRIP_TRAILING_WHITESPACE
)

# Add ImGui source files
set(IMGUI_DIR ${CMAKE_SOURCE_DIR}/external/imgui)
set(IMGUI_SOURCES
    ${IMGUI_DIR}/imgui.cpp
    ${IMGUI_DIR}/imgui_demo.cpp
    ${IMGUI_DIR}/imgui_draw.cpp
    ${IMGUI_DIR}/imgui_tables.cpp
    ${IMGUI_DIR}/imgui_widgets.cpp
    ${IMGUI_DIR}/backends/imgui_impl_glfw.cpp
    ${IMGUI_DIR}/backends/imgui_impl_opengl3.cpp
)

# Add nativefiledialog-extended
include(FetchContent)
FetchContent_Declare(
    nfd
    GIT_REPOSITORY https://github.com/btzy/nativefiledialog-extended.git
    GIT_TAG v1.1.1
)

# Add GoogleTest
FetchContent_Declare(
    googletest
    GIT_REPOSITORY https://github.com/google/googletest.git
    GIT_TAG v1.14.0
)

FetchContent_MakeAvailable(nfd googletest)

# Common source files
set(COMMON_SOURCES
    src/FileHandler.cpp
    src/ChapterDetector.cpp
    src/TextProcessor.cpp
    src/OCRWrapper.cpp
    src/OMRWrapper.cpp
)

set(COMMON_HEADERS
    src/FileHandler.h
    src/ChapterDetector.h
    src/TextProcessor.h
    src/OCRWrapper.h
    src/OMRWrapper.h
)

# CLI version
add_executable(Textbook_Divider_CLI main.cpp ${COMMON_SOURCES} ${COMMON_HEADERS})
target_include_directories(Textbook_Divider_CLI PRIVATE 
    src
    ${Python3_INCLUDE_DIRS}
    ${NumPy_INCLUDE_DIR}
    ${JNI_INCLUDE_DIRS}
)
target_link_libraries(Textbook_Divider_CLI PRIVATE 
    PoDoFo::PoDoFo
    Python3::Python
    ${JNI_LIBRARIES}
)

# Define source directory for Python module path for CLI
target_compile_definitions(Textbook_Divider_CLI PRIVATE
    SOURCE_DIR="${CMAKE_SOURCE_DIR}"
    BINARY_DIR="${CMAKE_BINARY_DIR}"
)


# GUI version (default)
add_executable(Textbook_Divider 
    src/gui/main_gui.cpp
    src/gui/GuiApp.cpp
    ${IMGUI_SOURCES}
    ${COMMON_SOURCES}
    ${COMMON_HEADERS}
)

target_include_directories(Textbook_Divider PRIVATE
    src
    ${IMGUI_DIR}
    ${IMGUI_DIR}/backends
    ${Python3_INCLUDE_DIRS}
    ${NumPy_INCLUDE_DIR}
    ${JNI_INCLUDE_DIRS}
)

target_link_libraries(Textbook_Divider PRIVATE
    OpenGL::GL
    glfw
    nfd
    PoDoFo::PoDoFo
    Python3::Python
    Python3::Module
    ${JNI_LIBRARIES}
)

# Add Python module path and site-packages to runtime environment
set_target_properties(Textbook_Divider PROPERTIES
    INSTALL_RPATH_USE_LINK_PATH TRUE
    BUILD_WITH_INSTALL_RPATH TRUE
    ENVIRONMENT "PYTHONPATH=${PYTHON_SITE_PACKAGES};CLASSPATH=${AUDIVERIS_JAR}"
)

set_target_properties(Textbook_Divider_CLI PROPERTIES
    INSTALL_RPATH_USE_LINK_PATH TRUE
    BUILD_WITH_INSTALL_RPATH TRUE
    ENVIRONMENT "PYTHONPATH=${PYTHON_SITE_PACKAGES};CLASSPATH=${AUDIVERIS_JAR}"
)

# Define source directory for Python module path
target_compile_definitions(Textbook_Divider PRIVATE
    SOURCE_DIR="${CMAKE_SOURCE_DIR}"
    BINARY_DIR="${CMAKE_BINARY_DIR}"
)

# Copy Python module to build directory
file(COPY ${CMAKE_SOURCE_DIR}/src/textbook_divider DESTINATION ${CMAKE_BINARY_DIR})

# Test executable
enable_testing()
add_executable(TextProcessor_Test
    tests/test_text_processor.cpp
    src/TextProcessor.cpp
)
target_include_directories(TextProcessor_Test PRIVATE
    src
    ${gtest_SOURCE_DIR}/include
)
target_link_libraries(TextProcessor_Test PRIVATE
    GTest::gtest
    GTest::gtest_main
)
include(GoogleTest)
gtest_discover_tests(TextProcessor_Test)

# Set GUI version as default target
set_property(DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR} PROPERTY VS_STARTUP_PROJECT Textbook_Divider)
