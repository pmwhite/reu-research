"""A modules for specifying how social networks can be walked or iterated
through."""
from collections import namedtuple
from itertools import chain
import graph

Walk = namedtuple('Walk', 'out_gen in_gen select_leaves')

def walk_edges(init, walk):
"Yields all the edges from a certain walk, starting from a specific node."
    nodes = {init}
    leaves = {init}
    while len(leaves) != 0:
        new_leaves = set()
        for leaf in walk.select_leaves(leaves):
            for out_node in walk.out_gen(leaf):
                new_leaves.add(out_node)
                yield (leaf, out_node)
            for in_node in walk.in_gen(leaf):
                new_leaves.add(in_node)
                yield (in_node, leaf)
        leaves = new_leaves - nodes
        nodes = nodes | leaves

def connections(x, walk):
"Gets a specific nodes 1-hop connections."
    return chain(walk.out_gen(x), walk.in_gen(x))

def degree(x, walk):
"Counts how many connections a node has."
    return len(list(connections(x, walk)))
