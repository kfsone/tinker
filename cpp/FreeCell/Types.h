#pragma once
// Specifically something_t types and aliases.

#include <array>
#include <vector>

#include "Constants.h"
#include "ForwardDeclare.h"


namespace FreeCell
{
	using positions_t = std::array<CardStack*, NUM_CARDS>;
	using cardset_t   = std::vector<Card>;
}

