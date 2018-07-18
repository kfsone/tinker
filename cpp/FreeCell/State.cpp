#include "stdafx.h"

#include <string>

#include "State.h"
#include "Deck.h"


namespace FreeCell
{
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

void validate(const std::string where, const FreeCell::State& data, const FreeCell::State::state_t& expect)
{
	if (data.data() == expect)
		return;

	throw std::runtime_error(where + ": data / expect mismatch");
}

void test_State()
{
	FreeCell::State test{};
	FreeCell::State::state_t expect{};
	validate("construction", test, expect);

	size_t pos = 0;

	// pos = 0
	pos = test.append(FreeCell::INVALID_CARD, pos);
	expect[0] = (FreeCell::INVALID_CARD << 2) & 255;
	validate("first byte", test, expect);

	// pos = 6
	pos = test.append(0, pos);
	validate("adding 0", test, expect);

	// pos = 12
	pos = test.append(1, pos);
	expect[2] = (1 << 6);
	validate("adding 1", test, expect);

	// pos = 18
	pos = test.append(2, pos);
	expect[2] |= 2;
	validate("adding 2", test, expect);

	// pos = 24
	pos = test.append(3, pos);
	expect[3] |= 3 << 2;
	validate("adding 3", test, expect);

	// pos = 30
	pos = test.append(37, pos);  // 100101
	expect[3] |= (37 >> 4); // 10 goes to #3, 0101 goes to #4
	expect[4] |= (37 << 4);
	validate("adding 100101", test, expect);

	pos = test.append(37, pos);  // 100101
	expect[4] |= 9; // 1001 goes to #4, 01 goes to #5
	expect[5] |= (1 << 6);
	validate("adding 100101", test, expect);

	pos = test.append(37, pos);  // 100101
	expect[5] |= 37;  // no shift.
	validate("adding 100101, no shift", test, expect);

	pos = test.append(37, pos); // 100101
	expect[6] |= 37 << 2;
	validate("adding 100101, shift 2", test, expect);

/*
       0        1       2       3       4       5      6       7       8

              111111111122222222223333333333444444444455555555556666666666777
    0123456789012345678901234567890123456789012345678901234567890123456789012
    |       |       |       |       |       |       |       |       |       |
    111111  |       |       |       |       |
          000000    |               |
            |   000001              |
            |       | 000010        |
            |       |       000011  |
            |       |             100101
            |       |                   100101
            |       |                         100101
            |       |                               100101
*/
}
