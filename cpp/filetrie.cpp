#include <array>
#include <iostream>
#include <memory>
#include <string>
#include <unordered_map>


#include <cstdint>

enum  { HashBits = 256 };
using hashpart_t  = uint16_t;
using hash_t      = std::array<hashpart_t, (HashBits / 8) / sizeof(hashpart_t)>;
enum { MaxDepth = HashBits / 8, PartSize = sizeof(hashpart_t) };

class Trie
{
    // Forward declares/typedefs.
    struct Node;
    using NodePtr     = std::unique_ptr<Node>;
    using PartMapping = std::unordered_map<hashpart_t, NodePtr>;
    using MapPtr      = std::unique_ptr<PartMapping>;

    // The trie is a graph of nodes. The hash '012345' would be
    // represented through a trie with [01] -> { [23] -> { [45] : {} }}
    struct Node
    {
        Node() : mOccupancy{0}, mMapping{PartMapping{}} {}
        explicit Node(size_t hashNo) : mOccupancy{1}, mHashNo{hashNo} {}

        // A node is a leaf when it only has one occupant
        bool isLeaf() const noexcept
        {
            return mOccupancy == 1;
        }

        bool getHash(hash_t* into) const noexcept
        {
            if (!isLeaf())
                return false;
            *into = mHashes[mHashNo];
            return true;
        }

        Node* addChild(size_t hashNo, int depth)
        {
            if (isLeaf())
            {
                // Leaves have a hash rather than a mapping, so we need
                // to replace the value with null and then add the previously
                // leaf value as a descendant leaf.

                // replace the old value with null but retain the old value
                size_t oldHashNo = std::exchange(mHashNo, 0ULL);

                // create the new mapping container
                mMapping = std::make_unique<PartMapping>();

                // Set the occupancy back to zero since the mapping is empty
                mOccupancy = 0;

                // We can re-call ourselves because occupancy is now 0 so we
                // aren't a leaf. When we return, we'll be back at occ == 1.
                addChild(oldHashNo, depth);
            }

            // Take the nTH chunk of the hash
            hashpart_t part = mHashes[hashNo][depth];

            // Insert as a leaf node, which are always pointers to hashes.
            auto entry = mMapping.emplace(part, hashNo);
            assert(entry.second == true);

            // Increment the number of hashes below us.
            ++mOccupancy;

            // Return the new node's pointer.
            return entry.first.get();
        }

        uint8_t     mOccupancy;         // The number of sub-hashes that have this hash part.
        union
        {
            size_t  mHashNo;            // When occupancy == 1, the unique hash below us.
            MapPtr  mMapping;           // When occupancy > 1, child nodes.
        }
    };

    // The trie itself is actually a node.
    Node        mRoot     {   };
    uint32_t    mMaxDepth { 0 };

    // But it tracks *all* hashes so we can index them.
    std::vector<hash_t> mHashes {};

public:
    Trie()
    {
        mHashes.reserve(50000);
    }

    uint8_t maxDepth()  const noexcept  { return mMaxDepth; }

    size_t size()       const noxcept   { return mHashes.size(); }

    void add(const hash_t& hash)
    {
        // Since duplicates are supposed to be very unlikely, we don't
        // check for duplicates. We naively add hashes and only check
        // if we exhaust unique parts to match against (i.e. a dupe)

        Node* cur = &mRoot;
        size_t depth = 0;
        while (true)
        {
            const hashpart_t part = hash[depth];

            // Has this node already seen this depth?
            auto it = cur->find(part);

            // Nope, add ourselves.
            if (it == cur->end())
            {
                cur->addChild(hash, depth++);
                break;
            }

            // Add a new child entry and take it's pointer to descend.
            cur = cur->addChild(hash, depth);

            depth++;

            // if we just reached MaxDepth, we found a duplicate.
            if (depth == MaxDepth)
                throw std::runtime_error("Duplicate found");
        }

        if (depth > mMaxDepth)
            mMaxDepth = depth;
    }

    // return false until you want to stop.
    using foreach_generator = bool(*)(const hash_t& hash, uint8_t length);

private:
    bool forEachImpl(foreach_generator gen, const Node* cur, uint8_t depth) const
    {
        if (cur->isLeaf())
            return gen(mHashes[cur->mHashNo]), depth);

        ++depth;
        for (auto&& mapping : *mMapping)
        {
            if (forEachImpl(gen, mapping.second.get(), depth))
                return true;
        }
        return false;
    }

public:
    bool forEach(foreach_generator gen) const
    {
        forEachImpl(gen, &mRoot, 1);
    }
};

int main()
{
    Trie trie {};
    while (!cin.fail())
    {
        std::string line {};
        cin.getline(line);
        if (line.empty())
            continue;

        // Read 2 hex digits per byte of partsize.
        hash_t hash {};
        const char* input = line.c_str();
        for (size_t i = 0; i < line.length(); i += 2 * PartSize)
        {
            // Convert from base 16 to an unsigned unit of partsize bits.
            hashpart_t part = std::stoul(line.substr(i, PartSize), 16);
            hash[i/PartSize] = part;
        }
        try
        {
            trie.add(hash);
        }
        catch (std::runtime_error& e)
        {
            std::cerr << "Duplicate found at '" << line << "'\n";
            return -1;
        }
    }

    std::cout << "Read " << hashes.size() << "hashes\n";
}