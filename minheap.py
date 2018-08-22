class MinHeap(object):

    def __init__(self):
        self.array = []
        self.__add = self.array.append
        self.__pop = self.array.pop

    def empty(self):
        return len(self.array) == 0

    def size(self):
        return len(self.array)

    def front(self):
        return self.array[0]

    def push_back(self, value):
        self.__add(value)
        sz = len(self.array)
        if sz > 1:
            self.heap_up(sz-1)

    def pop_front(self):
        array = self.array
        sz = len(array)
        if sz == 0:
            return None
        if sz == 1:
            return self.__pop
        poppedValue = array[0]
        array[0] = self.__pop
        self.heap_down(0)
        return poppedValue

    def replace_front(self, value):
        if len(self.array) == 0:
            self.push_back(value)
            return
        self.array[0] = value
        self.heap_down(0)

    def heap_down(self, node):
        array = self.array
        swapNode = node
        swapValue = array[node]
        size = len(array)
        child = (node * 2) + 1
        if child < size and array[child] < swapValue:
            swapNode = child
            swapValue = array[child]
        child += 1
        if child < size and array[child] < swapValue:
            swapNode = child
            swapValue = array[child]
        if swapNode is node:
            return
        array[swapNode] = array[node]
        array[node] = swapValue
        self.heap_down(swapNode)

    def heap_up(self, node):
        if node == 0:
            return
        array = self.array
        nodeValue = array[node]
        parentNode = (node - 1) >> 1
        parentValue = array[parentNode]
        if nodeValue < parentValue:
            array[parentNode] = nodeValue
            array[node] = parentValue
            self.heap_up(parentNode)
 
    def check_heap(self):
        array = self.array
        size = len(array)
        for node in range(1, size):
            nodeValue = array[node]
            if nodeValue < array[(node - 1) >> 1]:
                print("node %u !(%u < %u)" % node)
                return False
            child = (node << 1) + 1
            if child >= size:
                continue
            if array[child] < nodeValue:
                return False
            child += 1
            if child >= size:
                continue
            if array[child] < nodeValue:
                return False
        return True

    def dump_heap(self):
        size = len(self.array)
        if size == 0:
            print("heap is empty")
            return
        depth = len(bin(size)) - 2
        print("Heap contains %u elements, so %u levels" % (size, depth))

        nodeFormat = ' %2X '
        maxNodes = (1 << (depth - 1))
        nodeFormatWidth = len(nodeFormat % 0)
        graphWidth = maxNodes * nodeFormatWidth

        node = 0
        for d in range(0, depth):
            nodesOnLine = 1 << d
            padWidth = int(((graphWidth / nodesOnLine) - nodeFormatWidth) / 2)
            padding = ' ' * padWidth
            str = "%02u: " % (d)
            for n in range(0, nodesOnLine):
                value = (nodeFormat % self.array[node]) if node < size else " -- "
                str += padding + value + padding
                node += 1
            print(str)

