from collections import namedtuple
from itertools import chain
import graph

Walk = namedtuple('Walk', 'out_gen in_gen select_leaves')

def walk_edges(init, walk, conn):
    nodes = {init}
    leaves = {init}
    while len(leaves) != 0:
        new_leaves = set()
        for leaf in walk.select_leaves(leaves):
            for out_node in walk.out_gen(leaf, conn): 
                new_leaves.add(out_node)
                yield (leaf, out_node)
            for in_node in walk.in_gen(leaf, conn):
                new_leaves.add(in_node)
                yield (in_node, leaf)
        leaves = new_leaves - nodes
        nodes = nodes | leaves

def connections(x, walk, conn):
    return chain(walk.out_gen(x, conn), walk.in_gen(x, conn))

def degree(x, walk, conn):
    return len(list(connections(x, walk, conn)))
