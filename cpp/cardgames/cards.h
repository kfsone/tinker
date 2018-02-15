#pragma once

#include <array>
#include <cassert>
#include <string>
#include <string_view>
#include <vector>


namespace kfs
{
	struct non_copyable
	{
		non_copyable() = default;
		non_copyable(const non_copyable&) = delete;
		non_copyable& operator= (const non_copyable&) = delete;
	};

	struct non_moveable
	{
		non_moveable() = default;
		non_moveable(non_moveable&&) = delete;
		non_moveable& operator= (non_moveable&&) = delete;
	};
}


namespace cards
{

// ----------------------------------------------------------------------------
// Colors
//
constexpr size_t ColorCount = 2;
enum class Color
{
    Red, Black,
};
extern const std::string cColors[ColorCount];
enum class ColorBit
{
	Red   = 0x0,
	Black = 0x2,
};

//! Given a color, return the opposite color.
constexpr Color opposite_color(Color color_) { return (color_ == Color::Red) ? Color::Black : Color::Red; }


// ----------------------------------------------------------------------------
// Suites
//
constexpr size_t SuiteCount = 4;
constexpr uint32_t SuiteToColorShift = 1;
enum class Suite
{
    Hearts   = static_cast<uint32_t>(ColorBit::Red) + 0,
    Diamonds = static_cast<uint32_t>(ColorBit::Red) + 1,

    Clubs    = static_cast<uint32_t>(ColorBit::Black) + 0,
    Spades   = static_cast<uint32_t>(ColorBit::Black) + 1,
};
extern const std::string cSuites[SuiteCount];

constexpr Color suite_color(Suite suite) noexcept
{
	auto color_no = static_cast<uint32_t>(suite) >> SuiteToColorShift;
	return static_cast<Color>(color_no);
}
constexpr const std::string& label_suite(Suite suite) noexcept
{
	return cSuites[static_cast<uint32_t>(suite)];
}

extern Suite index_suite(std::string_view suite);


// ----------------------------------------------------------------------------
// Faces (the values a card can have)
//
constexpr size_t FaceCount = 13;
enum class Face
{
    Ace = 1,
    Two,    Three,      Four,       Five,
    Six,    Seven,      Eight,      Nine,
    Ten,    Jack,       Queen,      King,
};

constexpr Face LowFace = Face::Ace;
constexpr Face HighFace = Face::King;

// Verify that the cards appear to be contiguous.
static_assert(int(HighFace) - int(LowFace) + 1 == int(FaceCount), "Check Face values");

extern const std::string cFaces[FaceCount];

constexpr const std::string& label_face(Face face) noexcept
{
	return cFaces[static_cast<uint32_t>(face) - static_cast<uint32_t>(LowFace)];
}

extern Face index_face(std::string_view face);


// ----------------------------------------------------------------------------
// Card indexes - mapping a simple uint32_t to a card position.
//
//! How many cards per deck.
constexpr size_t DeckSize = SuiteCount * FaceCount;

using cardindex_t = uint8_t;
static_assert(DeckSize < 255, "Need a larger type for cardindex_t");

//! Return card index for a given suite/face
constexpr cardindex_t card_index(Suite suite_, Face face_) noexcept
{
	return static_cast<cardindex_t>(suite_) * FaceCount + static_cast<cardindex_t>(face_);
}

//! Return card index for a given label, e.g. 10H
cardindex_t card_index(std::string_view label_);

//! Extract the face (value) of a card from it's card index.
constexpr Face index_to_face(cardindex_t index_) noexcept
{
	// both indexes and faces are 1-based, but suites
	// are zero based. AH = 1, AD = 14, etc.
	return static_cast<Face>(((index_ - 1) % FaceCount) + 1);
}

//! Extract the suite of a card from it's card index.
constexpr Suite index_to_suite(cardindex_t index_) noexcept
{
	// both indexes and faces are 1-based, but suites
	// are zero based. AH = 1, AD = 14, etc.
	return static_cast<Suite>((index_ - 1) / FaceCount);
}

//! Extract the suite and face of a card from it's card index.
//! e.g. auto [suite, face] = index_to_card(index);
constexpr std::pair<Suite, Face> index_to_card(cardindex_t index_) noexcept
{
	return std::make_pair(index_to_suite(index_), index_to_face(index_));
}


// ----------------------------------------------------------------------------
// Tracking a deck of cards.
//

using deck_t = std::array<uint16_t, DeckSize>;

class Store;

class Card : public kfs::non_copyable, public kfs::non_moveable
{
	cardindex_t		mCardIndex{ 0 };
	Store*			mStore{ nullptr };
	Card*			mPrev{ nullptr };
	Card*			mNext{ nullptr };

public:
	constexpr Card(cardindex_t index_) noexcept : mCardIndex(index_) {}
	constexpr Card(Suite suite_, Face face_) noexcept : mCardIndex(card_index(suite_, face_)) {}

	Store* store() const noexcept { return mStore; }
	Card*  prev() const noexcept { return mPrev; }
	Card*  next() const noexcept { return mNext; }

	constexpr cardindex_t index() const noexcept { return mCardIndex; }
	constexpr Color color() const noexcept { return suite_color(suite()); }
	constexpr Suite suite() const noexcept { return index_to_suite(mCardIndex); }
	constexpr Face face() const noexcept { return index_to_face(mCardIndex); }
	std::string& name() const noexcept { return label_face(face()) + label_suite(suite()); }

	std::pair<Card*, Card*> append(Card* prev_) noexcept
	{
		if (prev_)
			prev_->mNext = this;
		return std::make_pair(prev_, nullptr);
	}

	std::pair<Card*, Card*> insert(Card* prev_, Card* next_) noexcept
	{
		mPrev, mNext = prev_, next_;
		if (mPrev)
			mPrev->mNext = this;
		if (mNext)
			mNext->mPrev = this;
		return std::make_pair(prev_, next_);
	}

	void detach() noexcept
	{
		if (mPrev)
			mPrev->mNext = nullptr;
		mPrev = nullptr;
	}

	std::pair<Card*, Card*> extract() noexcept
	{
		auto prev = mPrev;
		auto next = mNext;
		if (mPrev)
			prev->mNext = mNext;
		if (mNext)
			next->mPrev = prev;
		mPrev = mNext = nullptr;
		return std::make_pair(prev, next);
	}
};


class Store : public kfs::non_copyable, public kfs::non_moveable
{
protected:
	Card*	mHead;

public:
	virtual Card* head() const noexcept { return mHead;  }
	virtual Card* tail() const noexcept = 0;

	virtual size_t capacity() const noexcept = 0;

	virtual std::string name() const noexcept = 0;

	bool empty() const noexcept { return mHead == nullptr; }

	virtual size_t size() const noexcept = 0;

	//! Test if the given card can be added to this store.
	virtual bool accepts(Card*) const noexcept = 0;

	//! Returns previous/next cards this was inserted between.
	virtual std::pair<Card*, Card*> addCards(Card*) noexcept = 0;

	//! Remove the given card.
	virtual void removeCards(Card*, size_t numCards) noexcept = 0;

	//! Maximum number of cards we can move at once?
	virtual size_t maxMoveCards() const noexcept { return 1; }
};


}  // namespace cards
