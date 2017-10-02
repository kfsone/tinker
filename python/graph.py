# A simple exploration of graphs and various functions to work with them.

"""
A graph is a way of representing some kind of relationship between datum;
such as the distances between towns, the cost of a decision or the impact of
an action, latency between a server and users, the routes a packet could
take across a large network... The layout of a directory tree on a computer.

All kinds of things can be represented as one form or another of graph.

Typically each point of interest in the graph is called a Node. Nodes usually
have at least one interesting property (name, number, value) and the property
of having potentially one or more connections to other nodes.

Depending on nuances of the specific type of graph, nodes may be described
in other terms (parent, leaf, branch, root, etc) to describe their role
within the larger graph, but ultimately all of these are names for Nodes.

Again, the most important property of Nodes is their connectedness. The
connections between nodes are usually referred to as an Edge, and edges can
themselves have values and/or properties.

There is a wide spectrum of nomenclature for the elements of graphs, but they
can usually be reasoned relatively easily: a graph that flows in one
direction may refer to the nodes at the far end of edges as "descendants", or
"children"; if nodes have a maximum of two, directional edges, they may be
referred to as "binary nodes" or the edges may be referred to as "left" and
"right".

Most often such binary graphs produce what is commonly called a "tree".
A -> (B or C), B -> (D or E) ...


Examples:

    Family tree: Nodes represent family members, with a name as their values;
                 You could use bi-directional edges that represent a biological
                 link; or you could have uni-directional edges that are
                 labelled with what type of relationship (mother, father, son,
                 daughter).
    Junctions:   Nodes represent street intersections with edges representing
                 connections between them and the distance required to travel.

Although there are many kinds of graphs, there are also many, many core
algorithms common to all of them.

Consider the following "BinaryTreeNode". 'value' could be anything from a
simple number, to a string to a complex object in a database.

'left' and 'right' are optional edges linking to other Nodes.

A Tree would thus be formed by creating a "root" node, creating additional
nodes and associating them via the left or right members of other nodes.

Lets quickly build a tree to model how I might relay a card through a
series of friends, starting with myself and the person I want the card to reach:

    me = BinaryTreeNode("oliver")
    goal = BinaryTreeNode("john")

There are two people I might hand the card to who are likely to have connections
that would be able to forward it to John:

    meg = BinaryTreeNode("meg")
    jared = BinaryTreeNode("jared")

I'm going to (arbitrarily) assign one of these to be the "left" branch of my
tree and one the right:

    me.left = meg
    me.right = jared

I could just as easily have called them "up" and "down", "east" and "west",
"first" and "second".

    Both of these individuals have friends they could relay the card to:

    eva, nico = BinaryTreeNode("eva"), BinaryTreeNode("nico")
    meg.left, meg.right = eva, nico

Jared only knows one person, whether we assign this connection as left or
right is entirely up to us and/or the rules of our graph. I choose left.
Jared's friend knows someone called Bill who knows John.

    mark = BinaryTreeNode("mark")
    jared.left = mark
    bill = BinaryTreeNode("bill")
    mark.left = bill

Finally, lets say that both "Bill" and "Eva" know "john", the individual
I want the card forwarded to:

    bill.left, eva.left = goal

This series of relationships forms a Tree. We didn't need a discrete object
to describe it, we can essentially say:

    tree = me

(that is the "tree" is represented by the first node).

We could, if we wanted, create a discrete object/class for the tree, but that
is an option if we wanted to.

You might want to take a moment to draw this graph out and ask yourself what
information is present on it, what questions you might ask of it, and think
about what problems you might have accessing useful properties of this
structure.

"""


class BinaryTreeNode(object):

    # A 'binary tree' is nothing more than a hierarchy of nodes which
    # are connected 'downwards' by a maximum of two edges: left and right.

    def __init__(self, value):
        self.value = value
        self.left  = None
        self.right = None

# People
oliver = BinaryTreeNode("Oliver")
meg    = BinaryTreeNode("Meg")
jared  = BinaryTreeNode("Jared")
eva    = BinaryTreeNode("Eva")
nico   = BinaryTreeNode("Nico")
mark   = BinaryTreeNode("Mark")
bill   = BinaryTreeNode("Bill")
john   = BinaryTreeNode("John")

# The root of the tree and the goal of the exercise.
tree   = oliver
goal   = john

# Edges
oliver.left, oliver.right = meg, jared
meg.left, meg.right = eva, nico
jared.left = mark
eva.left = john
mark.left = bill
bill.left = john

# Questions:
# . How many nodes are in our graph? (without simply counting the list above)
# . What is the shortest path to 'goal'?
# . What is the longest path?
# . What is the average path?
# . How many distinct paths are there that reach John?
# . How many paths do *not* reach John?
# . Are there any loops?
# . How would you print all the nodes in the graph?
# . How would you print all the nodes in the graph that lead to john?


##### WORK IN PROGRESS #####
