#pragma once

#include "CardStack.h"
#include "CardSequence.h"

namespace FreeCell
{
	class Foundation : public CardStack
	{
	private:
		Suite           mSuite;
		std::string		mName;

	public:
		Foundation(Suite suite_)
			: CardStack(NUM_FACES)
			, mSuite(suite_)
			, mName("@" + gSuites[unsigned int(mSuite)])
		{}

		Suite suite() const noexcept { return mSuite; }

		virtual const std::string& name() const noexcept { return mName; }

		virtual bool accepting(ConstCardSequence seq_) const noexcept override
		{
			// Foundation only accepts card-at-a-time
			if (seq_.size() != 1)
				return false;
			auto& card = *(seq_.begin());
			if (card.suite() != suite())
				return false;
			// The face numbers match with the position in the cards array
			// each card is expected: empty => count == 0 => ace, etc.
			return static_cast<size_t>(card.face()) == size();
		}
	};
}

