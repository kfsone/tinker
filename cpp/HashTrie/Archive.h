#pragma once

#include <cstdint>
#include <limits>

// Extent (page) based archive format designed for file-systems capable of
// handling sparse files efficiently.
//
// The first extent is used for the archive header, allowing us to use
// block-based indexes for everything else while zero denotes invalid.
//
// Instead of using file names, we use hashes.

namespace Archive
{
	enum
	{

		Version = 1,

		ExtentSize = 4096,						// Bytes per extent

		// How many extents/bytes an archive can represent
		MaxExtentBits = 20,						// Max number of bits
		MaxExtents = (1 << MaxExtentBits) - 1,
		MaxArchiveSize = MaxExtents * ExtentSize,	// 2^20 * 4096 == 4GB

		MaxFileSizeBits = 28,						// Max bits for expressing a file size
		MaxFileSize = (1 << MaxFileSizeBits) - 1,	// 2^28 == 256MB

		// How many bits do we allow for file padding?
		InvalidExtent = 0,						// Nothing ever references the header
		StartExtent = 1,						// First valid extent id

		StartPrefix = 0x00,						// Value of the first prefix byte
		EndPrefix = 0xff,						// Value of the last prefix byte
		NumPrefixes = (EndPrefix - StartPrefix) + 1,
		MinHashLen = 3,							// We always store at least this many bytes
		MaxHashLen = 11,						// Maximum unique hash length we can handle

		MaxPrefixFiles = 256u,						// Maximum files a prefix can have
		MaxFiles = NumPrefixes * MaxPrefixFiles,
	};

	// We use 32-bit multiples of extent size to denote positions.
	using extentoff_t = uint32_t;
	// We use byte offsets relative to extent offsets, so 32-bits again.
	using byteoff_t = uint32_t;

	// We use a 4-byte moniker to identify file type and version.
	using ident_t = char[4];

	// Overall organization:
	// | ---- header ---- |  Size varies, but considered as extent 0.
	// | --v indexes  v-- |
	// | --  indexes   -- |  varies with file# and pfx len
	// | --^ indexes  ^-- |
	// --------------------
	// | - raw filedata - |  raw file data extent (#1)
	// | -- .......... -- |
	// --------------------  next file, extent #N
	// | - raw filedata - |

	struct Header
	{
		// Base   Byte Offset
		//  MetaData:
		// Offset |   0|   1|   2|   3|   4|   5|   6|   7
		// 0x0000  ------ident--------|------crc32--------
		// 0x0008  ---------------build no----------------
		// 0x0010  -------------created time--------------
		// 0x0018  ----file count-----|-------flags-------
		// 0x0020  p-00|p-01|p-02|p-03|p-04|p-05|p-06|p-07
		//   ..            ...       ...       ...
		// 0x0118  p-f8|p-f9|p-fa|p-fb|p-fc|p-fd|p-fe|p-ff
		// 0x0120  ---------------reserved----------------
		// 0x0140  

		ident_t     mIdent;							// +0x000 File type & version identifier
		uint32_t    mCrc32;							// +0x004 [optional] file crc
		uint64_t    mBuildNo;						// +0x008 Build this as generated from
		uint64_t    mCreatedTime;					// +0x010 Seconds since Unix epoch
		uint32_t	mFileCount;						// +0x018 Number of files (<=65535)
		uint32_t    mFlags;							// +0x01c flags
		uint8_t		mPfxFileCount[NumPrefixes];		// +0x020 Number of files in each prefix
		uint8_t		mUniqueLen[NumPrefixes];		// +00120 Max hash len for each prefix
		uint64_t	mReserved[4];					// +0x220 reserved
													// +0x240 (576 bytes)

		static_assert(MaxFiles - 1 <= std::numeric_limits<decltype(mFileCount)>::max(), "Type/Enum Mismatch");
		static_assert(MaxPrefixFiles - 1 == std::numeric_limits<decltype(*mPfxFileCount)>::max(), "Type/Enum Mismatch");
	};

	struct FileExtents		// Position (in extents) and length (in bytes) of files
	{
		uint64_t	mOffset : MaxExtentBits;		//  0-19 offset from BoF
		uint64_t	mLength : MaxFileSizeBits;		// 20-47 max file size of 256MB

													// Since you used the prefix to reach the index extent, we store the next 2
													// bytes of the hash right here. This will solve the lookup of the majority
													// of files. ATOW >50% of files only require 3 bytes of unique hash. This
													// also makes good use of cache lines.
		uint64_t	mHash1 : 8;						// 48-63 hashval[1] and hashval[2]
		uint64_t	mHash2 : 8;
	};
	enum { AdditionalHashParts = MaxHashLen - MinHashLen };
	using RemainingHashParts = uint8_t[AdditionalHashParts];

	static_assert(sizeof(FileExtents) == 8, "FileExtents size mismatch");

	// Each prefix extent is stored as a list of extent offsets, sizes and hashes.
	// This ordering allows the size of the hash list to vary with the prefix length.
	class PrefixIndex
	{
	private:
		// File positions, sizes and bytes 2 and 3 of each hash. Most lookups will be
		// done simply by querying this.
		FileExtents	mExtents[MaxPrefixFiles];		// 0000-07ff Base extent info
		static_assert(sizeof(mExtents) == ExtentSize / 2, "mExtents size mismatch");

		// Remainder of the block is taken up with remaining pieces of hash.
		// It is deliberately interwoven for the purpose of a tiny little bit of
		// data obfuscation.
		// This also takes us take up a single page.
		RemainingHashParts	mRemainingHashParts[MaxPrefixFiles];
		static_assert(sizeof(mRemainingHashParts) == ExtentSize / 2, "mRemainigHashParts size mismatch");

	public:
		const FileExtents* findFile(const Header& header, const uint8_t* hash) const;
	};
	static_assert(sizeof(PrefixIndex) == ExtentSize, "PrefixIndex size mismatch");

	struct ArchiveImage
	{
		union
		{
			Header			mHeader;					// "Block 0": Header
			uint8_t			_sizer[ExtentSize];
		};
		PrefixIndex		mPrefixIndex[NumPrefixes];		// Prefix indexes

		uint8_t			mData[0];						// beginning of data...
	};
	static_assert(sizeof(ArchiveImage) == ExtentSize + ExtentSize * NumPrefixes, "ArchiveImage size Mismatch");

	class Archive
	{
		ArchiveImage*		mImage;						// Memory mapping of block 0.

		const Header&			getHeader()					const { return mImage->mHeader; }
		const PrefixIndex&		getIndex(uint8_t prefix)	const { return mImage->mPrefixIndex[prefix]; }

		// Provide a mapping to the specified extents.
		const void* getMapping(const FileExtents& extents);

	public:
		// extent 0 is reserved for the header, so byte 0 is in extent 1.
		// note that 'extent 0' is actually more than one regular extent long.
		constexpr extentoff_t	convertByteToExtent(size_t size)			 const noexcept { return (size + ExtentSize - 1) / ExtentSize + 1; }

		// again, byte 0 of the data section is in extent 1
		constexpr size_t		convertExtentToByte(extentoff_t extent)      const noexcept { return (extent - 1) * ExtentSize; }

		constexpr size_t		convertByteOffsetToAbsolute(size_t offset)   const noexcept { return offset + sizeof(ArchiveImage); }

		// Determines if a file is in the archive. If mappedAddress is not null, provides a pointer to
		// a mapping of the file data. Optionally stores the size into size.
		bool					findFile(const uint8_t* hash, const void** mappedAddress, size_t* size);

		// Closes a file mapping
		void					closeFile(const void* mappedAddress);

	};
}

