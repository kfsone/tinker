#pragma once

#include "Constants.h"
#include "ForwardDeclare.h"
#include "Foundation.h"
#include "Spares.h"
#include "Column.h"


namespace FreeCell
{
	class Deck
	{
	private:
		Foundation      mFoundations[NUM_SUITES];
		Spares          mSpares;
		Column          mColumns[NUM_COLUMNS];

	public:
		Deck()
			: mFoundations{ Suite::Hearts, Suite::Diamonds, Suite::Clubs, Suite::Spades }
			, mSpares	  { NUM_SPARES }
			, mColumns	  { 1, 2, 3, 4, 5, 6, 7, 8 }
		{}

		~Deck() {}

		State getState() const;


		void play();
	};

}
