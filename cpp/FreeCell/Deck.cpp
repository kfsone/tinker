#include "stdafx.h"

#include "Deck.h"
#include "State.h"


namespace FreeCell
{
	void Deck::play()
	{
	}

	void Deck::addCard(Card card_, Placement place_, uint8_t placeIndex_/*=0*/)
	{
		// Ensure we haven't already added this card.
		if (mPositions[card_.index()] != nullptr)
			throw std::runtime_error("Duplicate " + card_.describe());

		// Find which card stack we're adding to.
		auto& cardStack = [=]() -> CardStack& {
			switch (place_)
			{
			case Placement::Foundation:
				return mFoundations[card_.suiteNo()];

			case Placement::Spare:
				return mSpares;

			case Placement::Column:
				return mColumns[placeIndex_];

			default:
				throw std::runtime_error("Invalid Placement");
			}
		}();

		// Add the card to the stack, which will populate it's position.
		cardStack.add(mPositions, card_);
	}

	std::string Deck::describe() const noexcept
	{
		static const std::string kEmptyCell = "    ";
		std::string result = "";

		result.reserve(NUM_CARDS * 5 + 64);

		// Print:
		//	   s1- s2- s3- s4-   fh- fd- fc- fs-
		//      c1- c2- c3- c4- c5- c6- c7- c8-
		for (size_t i = 0; i < NUM_SPARES; ++i)
		{
			uint8_t cardNo = mSpares.at(i);
			if (cardNo != INVALID_CARD)
				result += Card(cardNo).describe() + " ";
			else
				result += kEmptyCell;
		}

		result += "   ";

		for (size_t s = 0; s < NUM_SUITES; ++s)
		{
			if (!mFoundations[s].empty())
			{
				Suite   suite  = static_cast<Suite>(s);
				uint8_t faceNo = mFoundations[s].count();
				Face    face   = static_cast<Face>(faceNo);
				result += Card(suite, face).describe() + " ";
			}
			else
				result += kEmptyCell;
		}

		result += "\n\n";

		size_t maxRows{ 0 };
		std::for_each(mColumns.begin(), mColumns.end(), [&](auto& col_) { maxRows = std::max(maxRows, col_.size()); });
		for (size_t r = 0; r < maxRows; ++r)
		{
			result += " ";
			for (size_t c = 0; c < NUM_COLUMNS; ++c)
			{
				uint8_t cardNo = mColumns[c].at(r);
				result += (cardNo != INVALID_CARD)
							? Card(cardNo).describe() + " "
							: kEmptyCell;
			}
			result += "\n";
		}

		return result;
	}


	auto Deck::getState() const -> State
	{
		// Output will be:
		//  top card of each foundation :- NUM_SUITES,
		//  all the spares              :- NUM_SPARES,
		//  all column cards            :- <= NUM_CARDS
		//  column separators           :- NUM_COLUMNS

		State state{};
		size_t offset = 0;

		// Track the top card of each foundation.
		for (auto& f : mFoundations)
			offset = state.append(f.topCard(), offset);

		// Track spares until we get an invalid card.
		for (size_t i = 0; i < NUM_SPARES; ++i)
		{
			auto value = mSpares.at(i);
			offset = state.append(value, offset);
			if (value == INVALID_CARD)
				break;
		}

		// Build a sorted list of decks.
		std::array<const Column*, NUM_COLUMNS> columns;
		for (size_t i = 0; i < NUM_COLUMNS; ++i)
		{
			columns[i] = &mColumns[i];
		}
		std::sort(std::begin(columns), std::end(columns), [](const Column* lhs_, const Column* rhs_) {
			return *lhs_ < *rhs_;
		});
		for (auto& col : columns)
		{
			offset = state.append(INVALID_CARD, offset);
			for (auto& card : *col)
			{
				offset = state.append(card.value(), offset);
			}
		}

		return state;
	}
}

