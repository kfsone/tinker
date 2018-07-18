#include "stdafx.h"

#include <map>
#include <string>

#include "Constants.h"
#include "Labels.h"

namespace FreeCell
{

	static const std::map<std::string, FreeCell::Face>  gFaceLabels{
		{ "a", Face::Ace },
		{ "2", Face::Two },
		{ "3", Face::Three },
		{ "4", Face::Four },
		{ "5", Face::Five },
		{ "6", Face::Six },
		{ "7", Face::Seven },
		{ "8", Face::Eight },
		{ "9", Face::Nine },
		{ "10", Face::Ten },
		{ "j", Face::Jack },
		{ "q", Face::Queen },
		{ "k", Face::King }
	};

	static const std::map<std::string, FreeCell::Suite> gSuiteLabels{
		{ "h", Suite::Hearts },
		{ "d", Suite::Diamonds, },
		{ "c", Suite::Clubs },
		{ "s", Suite::Spades },
	};


	std::pair<Face, Suite> readLabel(const std::string& label)
	{
		if (label.size() < 2 || label.size() > 3)
			throw std::runtime_error("Illegal card label: " + label);

		std::string faceLabel{ label.c_str(), label.length() - 1 };
		std::string suiteLabel{ label.c_str() + label.length() - 1, 1 };

		auto faceIt = gFaceLabels.find(faceLabel);
		if (faceIt == gFaceLabels.end())
			throw std::runtime_error("Invalid face: " + label);

		auto suiteIt = gSuiteLabels.find(suiteLabel);
		if (suiteIt == gSuiteLabels.end())
			throw std::runtime_error("Invalid suite: " + label);

		return std::make_pair(faceIt->second, suiteIt->second);
	}
}
