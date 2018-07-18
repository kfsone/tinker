#pragma once

#include <string>

#include "CardStack.h"


namespace FreeCell
{
	class Spares : public CardStack
	{
	private:
		static inline const std::string sName{ "Sp" };

		virtual void arrange() noexcept override
		{
			if (size() > 1)
				std::sort(mCards.begin(), mCards.end());
		}

	public:
		Spares(size_t capacity_) : CardStack(capacity_) {}

		virtual const std::string& name() const noexcept { return sName; }

		virtual bool accepting(ConstCardSequence seq_) const noexcept override
		{
			return (seq_.size() > mCards.capacity() - mCards.size());
		}

		virtual void remove(ConstCardSequence seq_) override
		{
			if (seq_.size() != 1)
				throw std::runtime_error("spares can only be removed one-at-a-time");
			auto& card = *(seq_.begin());
			auto it = std::find(mCards.begin(), mCards.end(), card);
			if (it == mCards.end())
				throw std::runtime_error("trying to remove spare that's not present");
			swap_erase(it);
		}

		uint8_t at(size_t index_) const noexcept
		{
			return index_ < size() ? mCards[index_].value() : INVALID_CARD;
		}
	};
}

