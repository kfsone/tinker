#pragma once

#include "Card.h"
#include "CardSequence.h"
#include "Types.h"

namespace FreeCell
{
	class CardStack
	{
	protected:
		mutable cardset_t mCards;

		void swap_erase(cardset_t::iterator it_)
		{
			*it_ = mCards.back();
		}

		virtual void arrange() noexcept {}

	public:
		CardStack(unsigned int capacity_) { mCards.reserve(capacity_); }
		virtual ~CardStack() {}

		// Return the name of the stack
		virtual const std::string& name() const noexcept = 0;

		bool empty() const noexcept { return mCards.empty(); }
		auto size() const noexcept { return mCards.size(); }
		uint8_t count() const noexcept { return static_cast<uint8_t>(size()); }
		const Card& top() const noexcept { return mCards.back(); }

		CardSequence find(Card card_) noexcept
		{
			auto it = std::find(mCards.begin(), mCards.end(), card_);
			auto end = mCards.end();
			return (it != end) ? CardSequence{ it, it + 1 } : CardSequence{ end, end };
		}

		ConstCardSequence find(Card card_) const noexcept
		{
			auto it = std::find(mCards.cbegin(), mCards.cend(), card_);
			auto end = mCards.cend();
			return (it != end) ? ConstCardSequence{ it, it + 1 } : ConstCardSequence{ end, end };
		}

		virtual bool accepting(ConstCardSequence seq_) const noexcept = 0;

		// Add the following card(s)
		void add(positions_t& positions_, Card card_)
		{
			mCards.push_back(card_);
			card_.setLocation(positions_, this);
			arrange();
		}
		void add(positions_t& positions_, CardSequence seq_)
		{
			mCards.insert(std::end(mCards), seq_.begin(), seq_.end());
			std::for_each(seq_.begin(), seq_.end(),
				[this, &positions_](Card& card_) { card_.setLocation(positions_, this); }
			);
			arrange();
		}

		// Remove the given sequence of cards.
		virtual void remove(ConstCardSequence seq_)
		{
			if (seq_.size() > mCards.size())
				throw std::runtime_error("trying to remove too many cards");
			mCards.resize(mCards.size() - seq_.size());
		}

		// Return the contiguous sequence of cards at the top of this stack.
		virtual CardSequence topSequence() noexcept
		{
			return CardSequence{ std::end(mCards), std::end(mCards) };
		}

		ConstCardSequence topSequence() const noexcept
		{
			CardSequence result = const_cast<CardStack*>(this)->topSequence();
			return ConstCardSequence(result.begin(), result.end());
		}

		uint8_t topCard() const noexcept
		{
			return mCards.empty() ? INVALID_CARD : mCards.back().value();
		}
	};

}
