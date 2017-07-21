from collections import namedtuple
from itertools import islice, product, chain
import misc

def empty_graph():
    return {}

def add_edge(graph, f, t):
    if f not in graph:
        graph[f] = set()
    if t not in graph:
        graph[t] = set()
    graph[t].add(f)
    graph[f].add(t)

def pull_n_nodes(n, edges_iter):
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
    result = set()
    for f, connections in graph.items():
        for t in connections:
            if (f, t) not in result and (t, f) not in result:
                result.add((f, t))
    return result

def surrounding_nodes(graph, center):
    return misc.breadth_first_walk(center, lambda x: graph[x])

def union(g1, g2):
    return {node: g1.get(node, set()) | g2.get(node, set()) for node in chain(g1, g2)}

def seed(g1, g2, pred):
    return {(n1, n2) for n1, n2 in product(g1, g2) if pred(n1, n2)}

def zip_with(g1, g2, seeds, zipper):
    g1_mashed = {node: zipper(node, None) for node in g1}
    g2_mashed = {node: zipper(None, node) for node in g2}
    seed_data = {(n1, n2, zipper(n1, n2)) for n1, n2 in seeds}
    g1_seeds = {n1: mashed for n1, n2, mashed in seed_data}
    g2_seeds = {n2: mashed for n1, n2, mashed in seed_data}
    g1_convert = {**g1_mashed, **g1_seeds}
    g2_convert = {**g2_mashed, **g2_seeds}
    return {**{g1_convert[node]: {g1_convert[conn] for conn in connections} for node, connections in g1.items()},
            **{g2_convert[node]: {g2_convert[conn] for conn in connections} for node, connections in g2.items()}}
