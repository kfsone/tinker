#include "cards.h"

#include <algorithm>
#include <stdexcept>


namespace cards
{

// ----------------------------------------------------------------------------
// Strings

const std::string cColors[ColorCount] =
{
    "Red", "Black"
};

const std::string cSuites[SuiteCount] =
{
    "Hearts",
    "Diamonds",
    "Clubs",
    "Spades",
};

const std::string cFaces[FaceCount] =
{
    "A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"
};


// ----------------------------------------------------------------------------
// Helper functions

Suite index_suite(std::string_view suite_)
{
	for (size_t i = 0; i < SuiteCount; ++i)
	{
		if (cSuites[i][0] == suite_[0])
			return static_cast<Suite>(i);
	}
    throw std::runtime_error("Unrecognized suite: " + std::string(suite_));
}

Face index_face(std::string_view face)
{
    auto it = std::find(cbegin(cFaces), cend(cFaces), face);
    if (it == cend(cFaces))
        throw std::runtime_error("Unrecognized face: " + std::string(face));

	// Faces are 1-based.
    return static_cast<Face>(std::distance(cbegin(cFaces), it) + 1);
}

cardindex_t card_index(std::string_view label_)
{
	if (label_.size() < 2 || label_.size() > 3)
		throw std::invalid_argument("invalid card label: " + std::string(label_));

	auto splitPoint = label_.size() - 1;
	Face face = index_face(label_.substr(0, splitPoint));
	Suite suite = index_suite(label_.substr(splitPoint, 1));
	return card_index(suite, face);
}


}  // namespace cards
