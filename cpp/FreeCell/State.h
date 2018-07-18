#pragma once

#include <functional>
#include <string_view>

#include "Constants.h"


namespace FreeCell
{
	class State
	{
	public:
		//! \brief Number of card positions required to represent a deck's state.
		//! State comprises:
		//!     The face values of the top cards in each foundation using 4 bits each,
		//!     Contents of the Spare pile
		//!     Cards in the columns
		//!     INVALID_CARD separators between spares and columns, and between columns

		static constexpr size_t BITS_PER_SUITE = 2;
		static constexpr size_t BITS_PER_FACE = 4;
		static constexpr size_t BITS_PER_CARD = BITS_PER_FACE + BITS_PER_SUITE;
		static constexpr size_t CARD_MASK     = (1 << BITS_PER_CARD) - 1;
		static_assert((1 << BITS_PER_CARD) > (NUM_CARDS + 1), "Not enough bits per card");

		static constexpr size_t COLUMN_SEPARATORS = NUM_COLUMNS;

		static constexpr size_t NUM_SLOTS = NUM_SUITES + NUM_SPARES + NUM_CARDS + COLUMN_SEPARATORS;
		static constexpr size_t NUM_BITS  = NUM_SLOTS * BITS_PER_CARD;
		static constexpr size_t NUM_BYTES = ((NUM_BITS + 7) / 8 + 3) & ~3;	// round up to the next multiple of 3

		using state_t = std::array<uint8_t, NUM_BYTES>;

	private:
		state_t			mData {};

	public:
		constexpr State() : mData{}  {}

		constexpr const state_t data() const noexcept { return mData; }

		size_t append(uint8_t value_, size_t offset_)
		{
			auto bytePos   = offset_ / 8;
			auto firstBit  = offset_ & 0x07;

			value_ &= CARD_MASK;

			switch (firstBit)
			{
				case 0:
					mData[bytePos] |= value_ << 2;
					break;
				case 2:
					mData[bytePos] |= value_;
					break;
				case 4:
					// 4 bits in first byte, 2 bits in second byte
					mData[bytePos++] |= value_ >> 2;
					mData[bytePos]   |= value_ << 6;
					break;
				case 6:
					// 2 bits in first byte, 4 bits in second byte
					mData[bytePos++] |= value_ >> 4;
					mData[bytePos]   |= value_ << 4;
					break;
				default:
					throw std::runtime_error("Misalignment");
			}
			return offset_ + 6;
		}

		bool operator < (const State& rhs_) const noexcept		{ return mData < rhs_.mData; }
		bool operator == (const State& rhs_) const noexcept		{ return mData == rhs_.mData; }
		bool operator != (const State& rhs_) const noexcept		{ return mData != rhs_.mData; }

		auto hash() const noexcept
		{
			std::hash<std::u32string_view> hasher;
			return hasher(std::u32string_view{ reinterpret_cast<const char32_t*>(mData.data()), NUM_BYTES / sizeof(char32_t) });
		}
	};
}



