// FreeCell.cpp : Defines the entry point for the console application.
//

#include "stdafx.h"

#include <cctype>
#include <fstream>
#include <string>
#include <sstream>
#include <iostream>

#include "Labels.h"
#include "State.h"


extern void test_State();


[[noreturn]]
void usage(const char* exeName)
{
	printf("Usage: %s <deck file>\n", exeName);
	exit(0);
}

#include <map>

void readCards(const char* filename_, FreeCell::Deck& deck_)
{
	using namespace FreeCell;

	std::ifstream inf{ filename_ };
	std::string line, cardLabel;
	size_t cardsRead{ 0 };
	uint8_t columnNo{ 0 };

	Placement placing = Placement::Column;

	while (true)
	{
		std::getline(inf, line);
		if (inf.eof())
			break;
		if (line.empty() || std::isspace(line[0]))
			continue;
		if (line[0] == '[')
		{
			if (line == "[spare]")
				placing = Placement::Spare;
			else if (line == "[foundation]")
				placing = Placement::Foundation;
			else if (line == "[column]")
				placing = Placement::Column;
			else
				throw std::runtime_error("Unrecognized section: " + line);
			continue;
		}

		if (placing == Placement::Column && columnNo >= NUM_COLUMNS)
			throw std::runtime_error("Too many columns");

		std::istringstream istr{ line };
		while (!istr.eof())
		{
			istr >> cardLabel;
			if (istr.bad())
				throw std::runtime_error("Unrecognized card face: " + line);
			if (cardLabel.empty())
				break;
			auto[face, suite] = readLabel(cardLabel);
			deck_.addCard(Card{ suite, face }, placing, columnNo);
			++cardsRead;
		}
		if (placing == Placement::Column)
			++columnNo;
	}

	if (cardsRead != NUM_CARDS)
		throw std::runtime_error("Not enough cards read, got " + std::to_string(cardsRead));

	std::cout << "-- Loaded " << cardsRead << " from '" << filename_ << "'\n";
	std::cout << deck_.describe() << "\n";
	std::cout << deck_.getState().describe() << "\n";
	std::cout << deck_.getState().hash() << "\n";
}

int playDeck(const char* filename)
{
	FreeCell::Deck deck{};
	readCards(filename, deck);
	deck.play();
	return 0;
}


int main(int argc, const char* argv[])
{
	if (argc == 1)
	{
		test_State();
		return playDeck("TestDecks/TestDeck01.deck");
	}

	if (argc > 2 || strcmp(argv[1], "--help") == 0)
	{
		usage(argv[0]);
		return 0;
	}

	playDeck(argv[1]);

	return 0;
}

