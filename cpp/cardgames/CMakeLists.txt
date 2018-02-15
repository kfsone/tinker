CMAKE_MINIMUM_REQUIRED(VERSION 3.8)

SET(CMAKE_CXX_STANDARD 17)

SET(SOURCES

	cardgames.cpp

	cards.cpp
	freecell.cpp
)

SET(HEADERS

	cards.h
	freecell.h
)

ADD_EXECUTABLE(
	cardgames

	${SOURCES}

	${HEADERS}
)
