#include "HashTrie.h"


bool HashTrie::forEachImpl(foreach_generator gen, const Node* cur, uint8_t depth) const
{
	if (cur->getIsLeaf())
		return gen(cur->getHash(), depth);

	++depth;
	const Branch* branch = dynamic_cast<const Branch*>(cur);
	for (auto&& mapping : branch->getMapping())
	{
		if (forEachImpl(gen, mapping.second.get(), depth))
			return true;
	}
	return false;
}


HashTrie::Node* HashTrie::Branch::child(const hash_t& hash, size_t depth)
{
	mOccupancy++;
	HashTrie::unit_type part = hash[depth];
	auto it = mMapping.find(part);
	if (it == mMapping.end())
	{
		mMapping.emplace(part, std::make_unique<Leaf>(hash));
		return nullptr;
	}

	NodePtr& child = it->second;
	if (child->getIsLeaf())
	{
		// Convert leaf into branch containing one node, the old leaf.
		HashTrie::NodePtr oldLeaf = std::exchange(child, std::make_unique<Branch>());
		Branch* newBranch = dynamic_cast<Branch*>(child.get());
		// add the previous leaf as a child one level below its previous position
		newBranch->mMapping.emplace(oldLeaf->getHash()[++depth], std::move(oldLeaf));
		newBranch->mOccupancy++;
	}

	return child.get();
}


void HashTrie::add(const hash_t& hash)
{
	// Since duplicates are supposed to be very unlikely, we don't
	// check for duplicates. We naively add hashes and only check
	// if we exhaust unique parts to match against (i.e. a dupe)

	uint8_t depth = 0;
	HashTrie::Node* cur = &mRoot;
	while (true)
	{
		// Has this node already seen this part?
		cur = cur->child(hash, depth++);
		if (!cur)
		{
			// actual node is one deeper.
			++depth;
			break;
		}

		// If we reach max depth and the next node is not a leaf,
		// that means we ran out of distinguishing digits.
		if (depth == MaxUnits)
			throw std::runtime_error("Duplicate found");
	}

	if (depth > mMaxDepth)
		mMaxDepth = depth;
}


