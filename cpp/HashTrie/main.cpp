// HashTrie.cpp : Defines the entry point for the console application.
//

#include "HashTrie.h"

#include <cassert>
#include <chrono>
#include <cstdio>
#include <fstream>
#include <string>


static constexpr	size_t HexDigitsPerByte = 2;
static constexpr	size_t CharsPerUnit = HashTrie::UnitSize * HexDigitsPerByte;

static_assert(CharsPerUnit == 2, "Change the format mask");
#define		PPartHexFmt "%02X"


int main()
{
	HashTrie trie{};
	std::ifstream ins("hashes.txt");

	auto start = std::chrono::steady_clock::now();
	const char hexTokens[] = { "0123456789ABCDEF" };
	std::string line{};
	while (!ins.fail())
	{
		std::getline(ins, line);
		if (line.empty())
			continue;

		// Read 2 hex digits per byte of partsize.
		HashTrie::hash_t hash{};
		const char* input = line.c_str();

		for (size_t i = 0; i < HashTrie::MaxUnits * HashTrie::UnitSize; i += CharsPerUnit)
		{
			HashTrie::unit_type unit{};
			for (size_t j = 0; j < CharsPerUnit; j++)
			{
				unit <<= 4;
				const char* digit = strchr(hexTokens, *(input++));
				if (digit == nullptr)
					throw std::runtime_error("Invalid hex digit in filename: " + line);
				unit += static_cast<HashTrie::unit_type>(digit - hexTokens);
			}
			hash[i / CharsPerUnit] = unit;
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
	auto end = std::chrono::steady_clock::now();
	std::chrono::duration<double, std::milli> elapsedMs = end - start;

	static int counter = 0;
	static std::map<uint8_t, size_t> lengthCounts{};
	trie.forEach([](const HashTrie::hash_t& hash, uint8_t length) -> bool {
		lengthCounts[length]++;
		return false;
	});

	printf("Files: %zu, Max Depth: %u (%u bytes).\n", trie.size(), trie.maxDepth(), trie.maxDepth() * HashTrie::UnitSize);
	printf("Trie generation took: %.3fms\n", elapsedMs.count());
	for (uint32_t i = 1; i <= trie.maxDepth(); ++i)
	{
		printf(" Depth %u: %3zu files\n", i, lengthCounts[i]);
	}
}

