#pragma once

#include <vector>

#include "ForwardDeclare.h"
#include "Types.h"

namespace FreeCell
{
	template<typename ItT>
	struct Range
	{
		Range() {}
		Range(ItT begin_, ItT end_) : mBegin(begin_), mEnd(end_)
		{}

		ItT begin()		const noexcept { return mBegin; }
		ItT end()		const noexcept { return mEnd; }

		size_t size()	const noexcept { return std::distance(begin(), end()); }

	private:
		ItT				mBegin;
		ItT				mEnd;
	};

	using CardSequence      = Range<cardset_t::iterator>;
	using ConstCardSequence = Range<cardset_t::const_iterator>;
}
