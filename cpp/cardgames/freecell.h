#pragma once

#include "cards.h"

#include <list>
#include <memory>


namespace freecell
{
	using namespace cards;

	// ------------------------------------------------------------------------
	//! In Freecell the goal is to move all your cards into the corresponding
	//! Foundation for the cards' suites, in increasing order (ace->2->...->king)
	//
	class Foundation : public Store
	{
		Suite mSuite;
		Card* mTail{ nullptr };

	public:
		Foundation(Suite suite_) : mSuite(suite_) {}

		virtual std::string name() const noexcept override { return label_suite(mSuite) + " Foundation"; }
		virtual size_t capacity() const noexcept override { return FaceCount; }
		virtual size_t size() const noexcept override
		{
			return empty() ? 0 : static_cast<size_t>(mTail->face()) - static_cast<size_t>(mHead->face()) + 1;
		}
		virtual Card* tail() const noexcept override { return mTail; }

		virtual bool accepts(Card* card_) const noexcept override
		{
			// We shouldn't be trying to put cards of the wrong suite here.
			assert(card_->suite() == mSuite);
			auto topFaceNo = mTail ? 0 : static_cast<uint32_t>(mTail->face());
			return static_cast<uint32_t>(card_->face()) == topFaceNo + 1;
		}

		virtual std::pair<Card*, Card*> addCards(Card* card_) noexcept override
		{
			if (empty())
				mHead = card_;
			else
				card_->append(mTail);
			mTail = card_;
			return std::make_pair(card_->prev(), card_->next());
		}

		virtual void removeCards(Card* card_, size_t numCards_) noexcept override
		{
			mTail = card_->prev();
			card_->detach();
			if (mTail == nullptr)
				mHead = nullptr;
		}
	};

	// ------------------------------------------------------------------------
	//! Space for four cards regardless of order.
	//
	class Stash final : public Store
	{
	public:
		virtual std::string name() const noexcept override { return "Stash"; }
		virtual size_t capacity() const noexcept override { return 4; }
		virtual size_t size() const noexcept override
		{
			size_t size = 0;
			for (Card* cur = head(); cur; cur = cur->next())
				++size;

			return size;
		}

		virtual Card* tail() const noexcept override
		{
			if (!empty())
			{
				for (Card* cur = head(); ; cur = cur->next())
				{
					if (!cur->next())
						return cur;
				}
			}
			return nullptr;
		}

		virtual bool accepts(Card*) const noexcept override
		{
			return (size() < capacity());
		}

		// Keep cards in index order for simplicitly's sake.
		virtual std::pair<Card*, Card*> addCards(Card* card_) noexcept override
		{
			if (empty())
			{
				mHead = card_;
				return std::make_pair(nullptr, nullptr);
			}
			Card* prev = mHead;
			Card* next = mHead->next();
			while (next && prev->index() < card_->index())
			{
				prev = next, next = prev->next();
			}
			return card_->insert(prev, next);
		}

		virtual void removeCards(Card* card_, size_t numCards_) noexcept override
		{
			assert(numCards_ == 1);
			// we only deal with single removals.
			auto[prev, next] = card_->extract();
			if (mHead == card_)
				mHead = next;
			(void)prev;
		}
	};

	// ------------------------------------------------------------------------
	//! Columns in which the deck cards are accumulated.
	//
	class Stack : public Store
	{
		// Which vertical column this stack represents.
		uint8_t mColumn{ 0 };
		Card* mTail{ nullptr };
		Stack* mNextStack{ nullptr };
		size_t mNumCards;

	public:
		Stack(uint8_t column_) : mColumn(column_) {}

		void initialize(std::vector<Card*> cards_)
		{
			for (auto card : cards_)
			{
				if (empty())
					mHead = card;
				card->append(mTail);
				mTail = card;
				mNumCards++;
			}
		}

		virtual std::string name() const noexcept override
		{
			return "Stack #" + std::to_string(mColumn);
		}

		virtual Card* tail() const noexcept override { return mTail; }
		virtual size_t capacity() const noexcept override { return std::numeric_limits<decltype(capacity())>::max(); }
		virtual size_t size() const noexcept override { return mNumCards; }

		virtual size_t maxMoveCards() const noexcept override { return cards::FaceCount; }

		// Determine if we consider two cards to be contiguous.
		static constexpr bool is_contiguous(const Card* prev_, const Card* next_)
		{
			if (prev_->color() != opposite_color(next_->color()))
				return false;
			if (static_cast<uint32_t>(prev_->face()) != static_cast<uint32_t>(next_->face()) - 1)
				return false;
			return true;
		}

		//! Test if the given card can be added to this store.
		virtual bool accepts(Card* cards_) const noexcept override
		{
			// Cards must have decreasing value and alternating colors.
			if (!empty() && !is_contiguous(tail(), cards_))
				return false;
			for (Card* cur = cards_; cur->next(); cur = cur->next())
			{
				if (!is_contiguous(cur, cur->next()))
					return false;
			}
			return true;
		}

		//! Returns previous/next cards this was inserted between.
		virtual std::pair<Card*, Card*> addCards(Card* cards_) noexcept override
		{
			auto oldTail = mTail;
			if (empty())
				mHead = cards_;
			mTail = cards_;
			return cards_->append(oldTail);
		}

		//! Remove the given card.
		virtual void removeCards(Card* card_, size_t numCards_) noexcept override
		{
			// Run backwards from tail by <numCards_> -1 positions.
			Card* cur = tail();
			for (size_t i = 0; i < numCards_; ++i)
				cur = cur->prev();
			if (cur == nullptr)
				mHead = mTail = nullptr;
			assert(cur == nullptr || cur->next() == card_);
			card_->detach();
		}
	};


	class Game
	{
		cards::deck_t mStartingDeck;

		using foundations_t = std::list<Foundation>;
		using stash_t = std::unique_ptr<Stash>;
		using stacks_t = std::list<Stack>;

		foundations_t mFoundations;
		stash_t mStash;
		stacks_t mStacks;

	public:
		enum { NumStacks = 8 };

		Game();

		void initialize(cards::deck_t deck_);
	};

}  // namespace freecell
