"""A module for dealing with Graphs. It's a really simple module that probably
isn't the most performant. Using something like NetworkX would probably be
better, but this was the simplest way to get exactly what I wanted without
dealing with a somewhat magic library (If I actually new how NetworkX worked,
maybe it wouldn't seem so much like magic). I welcome any contributions to
convert this module and any module that uses it to NetworkX."""

from collections import namedtuple
from itertools import islice, product, chain
import misc

def empty_graph():
"""A graph is represented as a dictionary of connection sets; it is a very
redundant representation because each edge is counted twice, but we don't care
too much about memory usage."""
    return {}

def singleton(node):
"""A graph with a single node that has no edges."""
    return {node: set()}

def add_edge(graph, f, t):
"Destructively update the graph to have an edge between the given nodes."
    if f not in graph:
        graph[f] = set()
    if t not in graph:
        graph[t] = set()
    graph[t].add(f)
    graph[f].add(t)

def pull_n_nodes(n, edges_iter):
"""Starting with an empty graph, keep adding edges from the given iterator
until the graph has the specified number of nodes."""
    graph = empty_graph()
    prev_size = 0
    for f, t in edges_iter:
        add_edge(graph, f, t)
        size = len(graph) 
        if size > prev_size:
            misc.progress(n, size)
            prev_size = size
        if size >= n:
            break
    return graph

def edges(graph):
"An iterator of all the edges in the graph."
    result = set()
    for f, connections in graph.items():
        for t in connections:
            if (f, t) not in result and (t, f) not in result:
                result.add((f, t))
    return result

def size(graph):
"The number of nodes in the graph."
    return len(graph)

def surrounding_nodes(graph, center):
"""An iterator which yields the closest nodes to a given node; it progressively
moves outward until all nodes have been yielded"""
    return misc.breadth_first_walk(center, lambda x: graph[x])

def union(g1, g2):
"A combination of all the nodes and edges in two graphs"
    return {node: g1.get(node, set()) | g2.get(node, set()) for node in chain(g1, g2)}

def seed(g1, g2, pred):
"""Find all the possible pairs of nodes from two graphs which satisfy the given
predicate"""
    return {(n1, n2) for n1, n2 in product(g1, g2) if pred(n1, n2)}

def distances(g, center, nodes):
"""A dictionary of the distances that certain node has from several other
nodes. This function is useful for determining how far a user is from several
seeds."""
    result = {}
    remaining = set(nodes)
    for i, hop in enumerate(misc.hop_iter(center, lambda node: g[node])):
        distance = i + 1
        new_items = remaining.intersection(hop)
        for item in new_items:
            if item not in result:
                result[item] = distance
                remaining.remove(item)
        if len(remaining) == 0:
            break
    return result

def zip_with(g1, g2, seeds, zipper):
"""Combine two graphs into one using a given a zipping function. All edges are
preserved"""
    g1_mashed = {node: zipper(node, None) for node in g1}
    g2_mashed = {node: zipper(None, node) for node in g2}
    seed_data = {(n1, n2, zipper(n1, n2)) for n1, n2 in seeds}
    g1_seeds = {n1: mashed for n1, n2, mashed in seed_data}
    g2_seeds = {n2: mashed for n1, n2, mashed in seed_data}
    g1_convert = {**g1_mashed, **g1_seeds}
    g2_convert = {**g2_mashed, **g2_seeds}
    return {**{g1_convert[node]: {g1_convert[conn] for conn in connections} for node, connections in g1.items()},
            **{g2_convert[node]: {g2_convert[conn] for conn in connections} for node, connections in g2.items()}}
