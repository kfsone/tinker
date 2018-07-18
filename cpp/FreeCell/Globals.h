#pragma once

#include "Constants.h"

namespace FreeCell
{
			  static std::array<std::string, NUM_FACES>	gFaces { "a", "2", "3", "4", "5", "6", "7", "8", "9", "10", "j", "q", "k" };
	constexpr static std::array<char, NUM_SUITES>		gSuites{ 'h', 'd', 'c', 's' };
	constexpr static std::array<Color, NUM_SUITES>		gColors{ Color::Red, Color::Red, Color::Black, Color::Black };
}

