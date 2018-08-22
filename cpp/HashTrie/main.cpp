// HashTrie.cpp : Defines the entry point for the console application.
//

#include "HashTrie.h"

#include <cassert>
#include <fstream>
#include <string>
#include <cstdio>


static constexpr	size_t HexDigitsPerByte = 2;
static constexpr	size_t CharsPerUnit = HashTrie::UnitSize * HexDigitsPerByte;

static_assert(CharsPerUnit == 4, "Change the format mask");
#define		PPartHexFmt "%04X"


int main()
{
	HashTrie trie{};
	std::ifstream ins("hashes.txt");

	while (!ins.fail())
	{
		std::string line{};
		std::getline(ins, line);
		if (line.empty())
			continue;

		// Read 2 hex digits per byte of partsize.
		HashTrie::hash_t hash{};
		const char* input = line.c_str();

		for (size_t i = 0; i < HashTrie::MaxUnits * HashTrie::UnitSize; i += CharsPerUnit)
		{
			// Convert from base 16 to an unsigned unit of partsize bits.
			auto partHex = line.substr(i, CharsPerUnit);
			auto part = std::stoul(partHex, nullptr, 16);
			assert(part <= decltype(part)(std::numeric_limits<HashTrie::unit_type>::max()));
			hash[i / CharsPerUnit] = HashTrie::unit_type(part);
		}
		try
		{
			trie.add(hash);
		}
		catch (std::runtime_error& /*e*/)
		{
			fprintf(stderr, "Duplicate found at '%s'\n", line.c_str());
			return -1;
		}
	}


	trie.forEach([](const HashTrie::hash_t& hash, uint8_t length) -> bool {
		printf("%1u ", length);
		for (uint8_t i = 0; i < length; ++i) {
			printf(" 0x" PPartHexFmt "U,", hash.at(i));
		}
		printf("\n");

		return false;
	});

	printf("Files: %zu, Max Depth: %u (%u bytes).\n", trie.size(), trie.maxDepth(), trie.maxDepth() * HashTrie::UnitSize);
}
