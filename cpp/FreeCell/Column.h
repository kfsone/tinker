#pragma once

#include "CardStack.h"


namespace FreeCell
{

	class Column : public CardStack
	{
	private:
		uint32_t        mId;
		std::string		mName;

	public:
		// In theory, you could put everything into the one stack.
		Column(uint32_t id_)
			: CardStack(NUM_CARDS)
			, mId(id_)
			, mName("C" + std::to_string(mId))
		{}

		virtual const std::string& name() const noexcept { return mName; }

		virtual bool accepting(ConstCardSequence seq_) const noexcept override
		{
			///TODO:
			return false;
		}

		virtual CardSequence topSequence() noexcept override
		{
			if (size() < 2)
				return CardStack::topSequence();
			auto it = mCards.end() - 1;
			while (it != mCards.begin())
			{
				auto lower = *(it);
				auto upper = *(it - 1);
				if (!upper.follows(lower) || upper.color() == lower.color())
					break;
				--it;
			}
			return CardSequence{ it, mCards.end() };
		}

		// Const access iterators.
		using iterator_type = cardset_t::const_iterator;
		iterator_type begin()  const { return mCards.cbegin(); }
		iterator_type end()    const { return mCards.cend(); }

		friend static bool operator < (const CardStack& lhs, const CardStack& rhs) noexcept;

	};

	static inline bool operator < (const CardStack& lhs_, const CardStack& rhs_) noexcept
	{
		if (lhs_.size() < rhs_.size())
			return true;
		if (lhs_.size() == rhs_.size())
		{
			if (lhs_.topCard() > rhs_.topCard())
				return true;
		}
		return false;
	}
}
