#include "freecell.h"


namespace freecell
{

Game::Game()
{
	// Create a foundation for each suite.
	for (int suiteNo = 0; suiteNo < SuiteCount; ++suiteNo)
	{
		mFoundations.emplace_back(static_cast<Suite>(suiteNo));
	}

	// Allocate the stash.
	mStash = std::make_unique<Stash>();

	// Allocate the stacks for the cards themselves.
	for (int stackNo = 0; stackNo < NumStacks; ++stackNo)
	{
		mStacks.emplace_back(stackNo + 1);
	}
}

void Game::initialize(cards::deck_t deck_)
{

}

}
