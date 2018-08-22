#include <vector>			// it might be better to use a deque?
#include <iostream>
#include <cstdint>
#include <stdio.h>

template<typename ValueType>
class MinHeap
{
	std::vector<ValueType>	m_values;

public:
	typedef ValueType value_type;
	typedef MinHeap<ValueType> self_type;

	static size_t parentOfNode(size_t node) { return (node - 1) >> 1; }
	static size_t leftChildOfNode(size_t node) { return (node << 1) + 1; }

	size_t size() const { return m_values.size(); }
	bool empty() const { return m_values.empty(); }
	void clear() { m_values.clear(); }

	const value_type& front() const { return m_values[0]; }

private:
	void heap_down(size_t node)
	{
		const size_t heapSize = size();
		for (;;) {
			// find which node has the lowest value of node, leftChild and rightChild.
			size_t swapNode = node;
			// check the left child.
			size_t child = leftChildOfNode(node);
			if (child >= heapSize)
				return;
			if (m_values[child] < m_values[swapNode])
				swapNode = child;
			// check the right child.
			++child;
			if (child < heapSize && m_values[child] < m_values[swapNode])
				swapNode = child;
			else if (swapNode == node)
				return;
			std::swap(m_values[node], m_values[swapNode]);
			node = swapNode;
		}
	}

	void heap_up(size_t node)
	{
		while (node > 0) {
			size_t parentNode = parentOfNode(node);
			value_type& parentValue = m_values[parentNode];
			value_type& nodeValue = m_values[node];
			if (nodeValue < parentValue) {
				std::swap(parentValue, nodeValue);
				node = parentNode;
			} else {
				return;
			}
		}
	}

public:
	void pop_front()
	{
		if (empty())
			return;
		m_values[0] = m_values.back();
		m_values.pop_back();
		heap_down(0);
	}

	void push_back(const value_type& value)
	{
		const size_t nodePos = m_values.size();
		m_values.push_back(value);
		heap_up(nodePos);
	}
	
	void replace_front(const value_type& value)
	{
		if (size() == 0)
			push_back(value);
		else {
			m_values[0] = value;
			heap_down(0);
		}
	}
	
	bool check_heap() const
	{
		const size_t heapSize = size();
		for (size_t node = 1; node < heapSize; ++node) {
			// check that node is not < parent.
			if (m_values[node] < m_values[parentOfNode(node)])
				return false;
		}
		return true;
	}

	void dump_heap()
	{
		const size_t heapSize = size();
		size_t node = 0;
		for (size_t level = 0; node < heapSize; ++level) {
			std::cout << "|" << level << "| ";
			for (size_t col = 0; col < (1 << level); ++col) {
				if (node < heapSize)
					std::cout << m_values[node] << " ";
				else
					std::cout << "---" << " ";
				++node;
			}
		}
		std::cout << std::endl;
	}

private:
public:
	void sort()
	{
		const size_t heapSize = size();
		bool again;
		do {
			again = false;
			for (size_t node = 2; node < heapSize; ++node) {
				if (m_values[node] < m_values[node - 1]) {
					std::swap(m_values[node - 1], m_values[node]);
					heap_up(node - 1);
					again = true;
				}
			}
		} while (again);
	}
};

int main() {
	MinHeap<uint64_t> heap;
	heap.push_back(3);
	heap.push_back(2);
	heap.push_back(1);
	heap.dump_heap();
	if (!heap.check_heap()) {
		std::cout << "fail" << std::endl;
		return 0;
	}

	heap.push_back(10);
	heap.push_back(20);
	heap.push_back(30);
	heap.dump_heap();
	if (!heap.check_heap()) {
		std::cout << "fail" << std::endl;
		return 0;
	}

	heap.clear();
	heap.push_back(10);
	heap.push_back(20);
	heap.push_back(30);
	heap.dump_heap();
	if (!heap.check_heap()) {
		std::cout << "fail" << std::endl;
		return 0;
	}
	
	heap.push_back(1);
	heap.push_back(2);
	heap.push_back(3);
	heap.dump_heap();
	if (!heap.check_heap()) {
		std::cout << "fail" << std::endl;
		return 0;
	}

	heap.clear();
	heap.push_back(100);
	heap.push_back(200);
	heap.push_back(300);
	heap.push_back(30);
	heap.push_back(10);
	heap.push_back(20);
	heap.dump_heap();
	if (!heap.check_heap()) {
		std::cout << "fail" << std::endl;
		return 0;
	}

	heap.pop_front();
	heap.dump_heap();
	if (!heap.check_heap()) {
		std::cout << "fail" << std::endl;
		return 0;
	}

	heap.push_back(8);
	heap.push_back(7);
	heap.push_back(6);
	heap.push_back(3);
	heap.push_back(4);
	heap.push_back(5);
	heap.dump_heap();
	if (!heap.check_heap()) {
		std::cout << "fail" << std::endl;
		return 0;
	}

	heap.replace_front(1);
	heap.dump_heap();
	if (!heap.check_heap()) {
		std::cout << "fail" << std::endl;
		return 0;
	}
	
	heap.replace_front(1000);
	heap.dump_heap();
	if (!heap.check_heap()) {
		std::cout << "fail" << std::endl;
		return 0;
	}
	
	for (size_t i = 0; i < 8; ++i)
		heap.push_back(8);
	heap.dump_heap();
	if (!heap.check_heap()) {
		std::cout << "fail" << std::endl;
		return 0;
	}

	heap.replace_front(400);
	heap.push_back(9);
	heap.push_back(1);
	heap.push_back(1);
	heap.push_back(2);
	heap.push_back(9);
	heap.push_back(1005);
	heap.push_back(1010);
	heap.push_back(1008);
	heap.push_back(1004);
	heap.dump_heap();
	if (!heap.check_heap()) {
		std::cout << "fail" << std::endl;
		return 0;
	}

	heap.sort();
	heap.dump_heap();
	if (!heap.check_heap()) {
		std::cout << "fail" << std::endl;
		return 0;
	}
	
}
