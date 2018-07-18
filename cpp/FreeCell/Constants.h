#pragma once

#include <array>
#include <cstdint>
#include <string>


namespace FreeCell
{
	//! Possible card colors.
	enum class Color : uint8_t
	{
		Red, Black, _NumColors
	};


	//! Enumeration of all suites.
	enum class Suite : uint8_t
	{
		Hearts, Diamonds, Clubs, Spades, _NumSuites
	};


	//! Enumerations of card faces in value order.
	enum class Face : uint8_t
	{
		Ace, Two, Three, Four, Five, Six, Seven, Eight, Nine, Ten, Jack, Queen, King, _NumFaces
	};

	constexpr uint8_t INVALID_CARD = 255;						//! Constant for "no card".

	//! Enumerations of the cardstack types where things can be placed.
	enum class Placement : uint8_t
	{
		Column, Spare, Foundation
	};

	// Numeric values for the various enum'd constraints to reduce casting elsewhere.
	constexpr uint8_t NUM_COLORS = uint8_t(Color::_NumColors);	//! Pre-cast number of card colors.
	constexpr uint8_t NUM_SUITES = uint8_t(Suite::_NumSuites);	//! Pre-cast number of suites.
	constexpr uint8_t NUM_FACES  = uint8_t(Face::_NumFaces);	//! Pre-cast number of faces.
	constexpr uint8_t NUM_CARDS  = NUM_FACES * NUM_SUITES;		//! Pre-cast total number of cards.

	constexpr uint8_t NUM_COLUMNS = 8;				//! Number of columns that form the deck.
	constexpr uint8_t NUM_SPARES  = 4;				//! Number of spare card slots available.
}
