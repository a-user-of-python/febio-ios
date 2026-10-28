# Host harness build. Links the facade against a host FEBio build.
#   cmake -S HostHarness -B build-host-harness -DFEBIO_BUILD_DIR=<dir with lib/ and the FEBio source tree paths>
# FEBIO_SOURCE_DIR must point at the FEBio source checkout (for headers).
cmake_minimum_required(VERSION 3.20)
project(febio_host_harness CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

if(NOT FEBIO_BUILD_DIR)
	message(FATAL_ERROR "Set -DFEBIO_BUILD_DIR=<FEBio cmake build dir>")
endif()
if(NOT FEBIO_SOURCE_DIR)
	message(FATAL_ERROR "Set -DFEBIO_SOURCE_DIR=<FEBio source checkout>")
endif()

add_executable(febio_host_harness main.cpp ../App/febio_facade.cpp)

target_include_directories(febio_host_harness PRIVATE
	${FEBIO_SOURCE_DIR}
	${FEBIO_SOURCE_DIR}/FEBioLib
)

# FEBio module libraries (order matters for static archives; the host
# build produces shared libraries, where order is forgiving).
set(FEBIO_LIBS
	febiolib febiofluid febiomech febiomix febioopt febioplot
	febioxml feamr febiorve feimglib numcore fecore
)
foreach(lib IN LISTS FEBIO_LIBS)
	target_link_libraries(febio_host_harness PRIVATE ${FEBIO_BUILD_DIR}/lib/lib${lib}.so)
endforeach()
target_link_libraries(febio_host_harness PRIVATE z dl pthread)

set_target_properties(febio_host_harness PROPERTIES
	BUILD_RPATH ${FEBIO_BUILD_DIR}/lib)
