from collections import namedtuple
from itertools import islice
import misc

Graph = namedtuple('Graph', 'nodes edges')

def empty_graph():
    return Graph(nodes={}, edges=set())

def add_edge(graph, f, t):
    f_hash = misc.hash(f)
    t_hash = misc.hash(t)
    if f_hash not in graph.nodes:
        graph.nodes[f_hash] = f
    if t_hash not in graph.nodes:
        graph.nodes[t_hash] = t
    graph.edges.add((f_hash, t_hash))

def add_edges_from(graph, edges_iter):
    for f, t in edges_iter:
        add_edge(graph, f, t)

def from_edges(edges_iter):
    graph = empty_graph()
    add_edges_from(graph, edges_iter)
    return graph

def pull_n_nodes(n, edges_iter):
    graph = empty_graph()
    prev_size = 0
    for f, t in edges_iter:
        add_edge(graph, f, t)
        size = len(graph.nodes) 
        if size > prev_size:
            misc.progress(n, size)
            prev_size = size
        if size >= n:
            break
    return graph

def n_surrounding_nodes(graph, node_hash, n):
    edge_m = edge_map(graph)
    return islice(misc.breadth_first_walk(node_hash, lambda node: edge_m[node]), n)

def edge_map(graph):
    edge_sets = {key: set() for key, value in graph.nodes.items()}
    for f, t in graph.edges:
        edge_sets[f].add(t)
        edge_sets[t].add(f)
    return edge_sets

def union(g1, g2):
    return Graph(
            nodes={**g2.nodes, **g1.nodes},
            edges=(g1.edges | g2.edges))

def mash(g1, g2, seeds, masher):
    g1_mashed_nodes = {h1: masher(n1, None) for h1, n1 in g1.nodes.items()}
    g2_mashed_nodes = {h2: masher(None, n2) for h2, n2 in g2.nodes.items()}
    seed_data = {(h1, h2): masher(g1.nodes[h1], g2.nodes[h2]) for h1, h2 in seeds}
    g1_seed_nodes = {h1: seed for (h1, h2), seed in seed_data.items()}
    g2_seed_nodes = {h2: seed for (h1, h2), seed in seed_data.items()}
    g1_convert = {**g1_mashed_nodes, **g1_seed_nodes}
    g2_convert = {**g2_mashed_nodes, **g2_seed_nodes}
    all_nodes = set(g1_convert.values()).union(g2_convert.values())
    all_edges = {(misc.hash(g1_convert[f]), misc.hash(g1_convert[t])) for f, t in g1.edges}.union(
            (misc.hash(g2_convert[f]), misc.hash(g2_convert[t])) for f, t in g2.edges)
    return Graph(
            nodes={misc.hash(node): node for node in all_nodes}, 
            edges=all_edges)
