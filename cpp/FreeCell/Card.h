#pragma once

#include <string>

#include "Constants.h"
#include "ForwardDeclare.h"
#include "Globals.h"
#include "Types.h"


namespace FreeCell
{
	//! @brief	Description of a single card - suite and face.
	//!
	//! Both suite and face can be accessed as either enum classes
	//! or integer values (suiteNo, faceNo).
	//
	class Card final
	{
	private:
		union
		{
			struct
			{
				Suite               mSuite : 4;
				Face                mFace : 4;
			};
			struct
			{
				uint8_t             mSuiteNo : 4;
				uint8_t             mFaceNo : 4;
			};
			uint8_t					mValue = INVALID_CARD;
		};


	public:
		constexpr Card() noexcept {}
		constexpr Card(Suite suite_, Face face_) noexcept
			: mSuite(suite_), mFace(face_) {}
		constexpr Card(uint8_t value_) noexcept : mValue{ value_ } {}

		std::string describe()		const noexcept { return ((mFace == Face::Ten) ? "" : " ") + gFaces[mFaceNo] + gSuites[mSuiteNo]; }

	public:
		constexpr auto suite()		const noexcept { return mSuite; }
		constexpr auto face()		const noexcept { return mFace; }
		constexpr auto suiteNo()	const noexcept { return mSuiteNo;  }
		constexpr auto faceNo()     const noexcept { return mFaceNo; }
        constexpr auto color()		const noexcept { return gColors[mSuiteNo]; }
		constexpr auto value()      const noexcept { return mValue; }

		constexpr uint8_t index()	const noexcept { return (mFaceNo * NUM_SUITES) + mSuiteNo; }

		constexpr bool operator == (const Card rhs_) const noexcept { return mValue == rhs_.mValue; }
		constexpr bool operator <  (const Card rhs_) const noexcept { return mValue <  rhs_.mValue; }
		constexpr bool operator <= (const Card rhs_) const noexcept { return mValue <= rhs_.mValue; }
		constexpr bool operator >  (const Card rhs_) const noexcept { return mValue >  rhs_.mValue; }
		constexpr bool operator >= (const Card rhs_) const noexcept { return mValue >= rhs_.mValue; }

		constexpr bool operator == (Face face_)		 const noexcept { return mFace == face_; }
		constexpr bool operator <  (Face face_)		 const noexcept { return mFace <  face_; }
		constexpr bool operator <= (Face face_)		 const noexcept { return mFace <= face_; }
		constexpr bool operator >  (Face face_)		 const noexcept { return mFace >  face_; }
		constexpr bool operator >= (Face face_)		 const noexcept { return mFace >= face_; }

		constexpr bool operator == (Suite suite_)	 const noexcept { return mSuite == suite_; }
		constexpr bool operator <  (Suite suite_)	 const noexcept { return mSuite <  suite_; }
		constexpr bool operator <= (Suite suite_)	 const noexcept { return mSuite <= suite_; }
		constexpr bool operator >  (Suite suite_)	 const noexcept { return mSuite >  suite_; }
		constexpr bool operator >= (Suite suite_)	 const noexcept { return mSuite >= suite_; }

		constexpr bool preceedes(const Card next_)	 const noexcept
		{
			return mFaceNo + 1 == next_.mFaceNo;
		}

		constexpr bool follows(const Card next_)	 const noexcept
		{
			return next_.preceedes(*this);
		}

		// Record where I am on the deck.
		void setLocation(positions_t& positions_, CardStack* stack_) const
		{
			positions_[index()] = stack_;
		}

		// Retrieve where I am on the deck.
		CardStack* getLocation(positions_t& positions_) const
		{
			return positions_[index()];
		}
	};

}

