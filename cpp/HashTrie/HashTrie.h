#pragma once

#include <array>
#include <cstdint>
#include <memory>
#include <map>


class NodeAllocator;

// Builds a Trie based on 256-bit (32 byte) hex hashes, determining
// the maximum number of 'units' (2-byte values) required to uniquely
// identify
class HashTrie final
{
public:
	static constexpr	size_t HashBits = 256;
	using				unit_type = uint8_t;

	static constexpr	size_t UnitSize = sizeof(unit_type);
	static constexpr	size_t MaxUnits = HashBits / (8 * UnitSize);

	using				hash_t = std::array<unit_type, MaxUnits>;

private:
	// Forward declares/typedefs.
	class Node;
	using NodePtr = std::unique_ptr<Node>;
	using UnitMap = std::map<unit_type, NodePtr>;

	// Base class for describing nodes in the trie.
	class Node
	{
	public:
		Node() = default;
		virtual ~Node() = default;

		virtual bool		getIsLeaf()					const	noexcept = 0;
		virtual uint32_t	getOccupancy()				const	noexcept = 0;
		virtual hash_t		getHash()					const	noexcept { return hash_t{}; }

		virtual	Node* child(const hash_t& hash, size_t depth) = 0;
	};


	// Leaf nodes represent unique hashes, points in the trie where there is only
	// a single descendant.
	class Leaf final : public Node
	{
		hash_t	mHash;

	public:
		Leaf(const hash_t& hash_) : mHash{ hash_ } {}
		virtual ~Leaf() {}

		virtual bool		getIsLeaf()					const	noexcept override { return true; }
		virtual uint32_t	getOccupancy()				const	noexcept override { return 1; }
		virtual hash_t		getHash()					const	noexcept override { return mHash; }
		virtual Node*		child(const hash_t& hash, size_t depth)		 override { throw std::logic_error("Unbranched leaf."); }
	};


	// Branch nodes denote sequences of hash-units that do not yet describe a unique hash.
	// E.g given the hashes { 0001, 0002 } and a unit size of 1 byte, node 00 is a branch with
	// 00->01 and 00->02 as leaves.
	//
	class Branch : public Node
	{
	protected:
		UnitMap		mMapping{};
		uint32_t	mOccupancy{ 0 };

	public:
		Branch() = default;
		virtual ~Branch() = default;

		virtual bool		getIsLeaf()					const	noexcept override { return false; }
		virtual uint32_t	getOccupancy()				const	noexcept override { return mOccupancy; }
		virtual Node*		child(const hash_t& hash, size_t depth)		 override;

		const UnitMap&		getMapping()				const	noexcept { return mMapping; }
	};


	// Describes the 'Root' node used by the trie, which differs from a regular branch in that it
	// exposes access to the 'clear' function.
	//
	class Root final : public Branch
	{
	public:
		virtual ~Root() = default;
		void clear()
		{
			mMapping.clear();
			mOccupancy = 0;
		}
	};

	friend class NodeAllocator;

	// The top-level Branch forms the root of the trie.
	Root		mRoot{};

	// Track the maximum depth during construction.
	uint32_t    mMaxDepth{ 0 };


public:
	// Default constructor
	HashTrie() = default;
	~HashTrie() = default;

	// Clear the root node and reset max depth.
	void clear();

	// Accessors
	auto   maxDepth()	const noexcept { return mMaxDepth; }
	size_t size()       const noexcept { return mRoot.getOccupancy(); }

	// Add a new hash to the trie -- throws on adding a duplicate.
	void add(const hash_t& hash);

	// Execute a given function on all leaf nodes. Function should true to stop
	// the loop early.
	using foreach_generator = bool(*)(const hash_t& hash, uint8_t length);
	inline bool forEach(foreach_generator gen) const
	{
		return forEachImpl(gen, &mRoot, 1);
	}

private:
	bool forEachImpl(foreach_generator gen, const Node* cur, uint8_t depth) const;
};


