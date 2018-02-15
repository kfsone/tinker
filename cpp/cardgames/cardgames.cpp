#include "cards.h"
#include "freecell.h"

#include <iostream>


cards::deck_t readStartingDeck()
{
	cards::deck_t deck{};
	size_t cardNo = 0;

	// we read the cards left-to-right, top down.
	for (std::string label; std::getline(std::cin, label);)
	{
		auto idx = cards::card_index(label);
		if (deck[idx-1] != 0)
			throw std::invalid_argument("duplicate card: " + label);

		// Indexes and positions are 1-based.
		deck[idx-1] = static_cast<uint16_t>(++cardNo);
	}

	return deck;
}

int main(int argc, const char* argv[])
{
	// Read the deck from stdin.
	try
	{
		cards::deck_t startingDeck = readStartingDeck();
		std::cout << "Loaded deck.\n";

		freecell::Game game{};
		game.initialize(startingDeck);

	}
	catch (const std::exception& e)
	{
		std::cerr << "error: " << e.what() << "\n";
		return -1;
	}
}
