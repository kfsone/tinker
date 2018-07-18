// FreeCell.cpp : Defines the entry point for the console application.
//

#include "stdafx.h"

#include <cctype>
#include <fstream>
#include <string>
#include <sstream>

#include "Labels.h"
#include "State.h"


extern void test_State();


namespace FreeCell
{
	void Deck::play()
	{
	}
}

[[noreturn]]
void usage(const char* exeName)
{
	printf("Usage: %s <deck file>\n", exeName);
	exit(0);
}

#include <map>

void readCards(const char* filename, FreeCell::Deck& deck)
{
	using namespace FreeCell;

	std::ifstream inf{ filename };
	std::string line, cardLabel;
	size_t cardsRead{ 0 };
	size_t columnNo{ 0 };

	enum class Section { Column, Foundation, Spare };
	Section section = Section::Column;

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
				section = Section::Spare;
			else if (line == "[foundation]")
				section = Section::Foundation;
			else if (line == "[column]")
				section = Section::Column;
			else
				throw std::runtime_error("Unrecognized section: " + line);
			continue;
		}

		std::vector<std::pair<Suite, Face>> cards;
		std::istringstream istr{ line };
		while (true)
		{
			istr >> cardLabel;
			if (istr.eof())
				break;
			auto[face, suite] = readLabel(cardLabel);
		}
	}
}


int main(int argc, const char* argv[])
{
	if (argc < 2 || strcmp(argv[1], "--help") == 0)
	{
		usage(argv[0]);
	}

	FreeCell::Deck deck {};

	readCards(argv[1], deck);

	return 0;
}

