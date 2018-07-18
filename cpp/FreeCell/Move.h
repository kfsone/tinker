#pragma once

#include <array>

#include "CardSequence.h"
#include "CardStack.h"


namespace FreeCell
{

	class Move
	{
	public:
		enum class Placement { Foundation, Spare, Deck };
		using move_t = std::array<Card, NUM_FACES>;

	protected:
		Card	mTopCard;		//! Top card of the movement
		Card	mDestCard;		//! The card we're placing to
		uint8_t	mNumCards;		//! Number of cards being moved

	public:
		Move(Card topCard_, Card destCard_, uint8_t numCards_=1)
			: mTopCard(topCard_), mDestCard(destCard_)
			, mNumCards(numCards_)
		{}

		const Card&	topCard()  const noexcept { return mTopCard; }
		const Card&	destCard() const noexcept { return mDestCard; }
		virtual size_t size()  const noexcept { return mNumCards; }
	};

}
