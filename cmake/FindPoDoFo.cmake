# Find PoDoFo PDF library
# Sets:
#   PODOFO_FOUND
#   PODOFO_INCLUDE_DIRS
#   PODOFO_LIBRARIES

find_path(PODOFO_INCLUDE_DIR
	NAMES podofo/podofo.h
	PATH_SUFFIXES podofo
)

find_library(PODOFO_LIBRARY
	NAMES podofo
)

include(FindPackageHandleStandardArgs)
find_package_handle_standard_args(PoDoFo
	REQUIRED_VARS
		PODOFO_LIBRARY
		PODOFO_INCLUDE_DIR
)

if(PoDoFo_FOUND AND NOT TARGET PoDoFo::PoDoFo)
	add_library(PoDoFo::PoDoFo UNKNOWN IMPORTED)
	set_target_properties(PoDoFo::PoDoFo PROPERTIES
		IMPORTED_LOCATION "${PODOFO_LIBRARY}"
		INTERFACE_INCLUDE_DIRECTORIES "${PODOFO_INCLUDE_DIR}"
	)
endif()

mark_as_advanced(PODOFO_INCLUDE_DIR PODOFO_LIBRARY)