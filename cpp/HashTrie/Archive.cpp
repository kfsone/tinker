#include "Archive.h"
#include <cstring>


namespace Archive
{

	const FileExtents* PrefixIndex::findFile(const Header& header, const uint8_t* lookupHash) const
	{
		///TODO: Binary search
		const size_t numFiles = header.mPfxFileCount[lookupHash[0]];
		const size_t uniqueLen = header.mUniqueLen[lookupHash[0]];

		// Start at the second byte of the hash, because we used the first to get here.
		const FileExtents* const begin = mExtents;
		const FileExtents* const end = mExtents + numFiles;
		for (const FileExtents* cur = begin; cur < end; ++cur)
		{
			if (cur->mHash1 < lookupHash[1])
				continue;
			if (cur->mHash1 > lookupHash[1])
				break;
			if (cur->mHash2 > lookupHash[2])
				break;
			if (cur->mHash2 < lookupHash[2])
				continue;
			if (uniqueLen == MinHashLen)
				return cur;

			// Match, now we need to compare the remainder.
			size_t fileNo = static_cast<size_t>(cur - begin);
			if (std::memcmp(mRemainingHashParts, lookupHash + MinHashLen, uniqueLen - MinHashLen) == 0)
				return cur;
		}
	}

	const void* Archive::getMapping(const FileExtents& extents)
	{
		///TODO: Implement
		return nullptr;
	}

	bool Archive::findFile(const uint8_t* hash, const void** mappedTo, size_t* size)
	{
		auto pfxFileCount = getHeader().mPfxFileCount[hash[0]];
		if (pfxFileCount == 0)
			return false;

		auto uniqueLenForPfx = getHeader().mUniqueLen[hash[0]];
		const PrefixIndex& prefixIndex = getIndex(hash[0]);

		const FileExtents* extents = getIndex(hash[0]).findFile(getHeader(), hash);
		if (extents == nullptr)
			return false;

		if (mappedTo)
			*mappedTo = getMapping(*extents);

		if (size)
			*size = extents->mLength;

		return true;
	}

	void Archive::closeFile(const void* mappedAddress)
	{
		///TODO: Implement
	}
}
