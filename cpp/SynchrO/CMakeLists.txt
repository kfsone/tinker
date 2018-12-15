cmake_minimum_required (VERSION 3.8)

add_subdirectory (Libraries)

set(
	SYNCHRO_SOURCES

	"SynchrO.cpp"
	"SynchrO.h"
)

set(
	SYNCHRO_LIBRARIES

	clsocket
)

add_executable(
	SynchrO

	${SYNCHRO_SOURCES}	
)

target_link_libraries(
	SynchrO

	${SYNCHRO_LIBRARIES}
)



