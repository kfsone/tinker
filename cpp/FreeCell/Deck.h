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
		using Foundations = std::array<Foundation, NUM_SUITES>;
		using Columns     = std::array<Column, NUM_COLUMNS>;

		Spares			mSpares;
		Foundations		mFoundations;
		Columns			mColumns;

		positions_t		mPositions;

	public:
		Deck()
			: mFoundations{ Suite::Hearts, Suite::Diamonds, Suite::Clubs, Suite::Spades }
			, mSpares	  { NUM_SPARES }
			, mColumns	  { 1, 2, 3, 4, 5, 6, 7, 8 }
			, mPositions  {}
		{
		}

		~Deck() {}

		std::string describe() const noexcept;

		State getState() const;

		void addCard(Card card_, Placement place_, uint8_t placeIndex_=0);

		const Foundation& foundation(Suite suite_) const noexcept { return mFoundations[static_cast<uint8_t>(suite_)]; }
		const Spares&     spares()                 const noexcept { return mSpares; }
		const Column&     column(uint8_t col_)     const noexcept { return mColumns[col_]; }

		      Foundation& foundation(Suite suite_) noexcept { return mFoundations[static_cast<uint8_t>(suite_)]; }
		      Spares&     spares()                 noexcept { return mSpares; }
		      Column&     column(uint8_t col_)     noexcept { return mColumns[col_]; }

		void play();
	};

}
