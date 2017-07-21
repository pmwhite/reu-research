from itertools import islice, product, combinations
from visualization import GexfWritable
from network import walk_edges
from collections import namedtuple
import random
import misc
import graph

AttackerData = namedtuple('AttackerData', 'target aux known_seeds t_nodes a_nodes')
Table = namedtuple('Table', 'matrix columns rows')

def jaccard_index(s1, s2):
    return len(s1 & s2) / len(s1 | s2)

def table_apply(items1, items2, f):
    return Table(
            matrix=[[f(item1, item2) for item2 in items2] for item1 in items1], 
            columns=items1, 
            rows=items2)

def jaccard_simple(attacker_data, threshold):
    t_edge_map = graph.edge_map(attacker_data.target)
    a_edge_map = graph.edge_map(attacker_data.aux)
    def expand(node, edge_map):
        return set(islice(misc.breadth_first_walk(node, lambda n: edge_map[n]), 200))
    t_surround_map = {t: expand(t, t_edge_map) for t in attacker_data.t_nodes}
    converted_t_surround = {
            t: {attacker_data.known_seeds.get(connection, connection) for connection in connections}
            for t, connections in t_surround_map.items()}
    a_surround_map = {a: expand(a, a_edge_map) for a in attacker_data.a_nodes}
    return {(t, a, jaccard_index(converted_t_surround[t], a_surround_map[a]) > threshold)
        for t, a in product(attacker_data.t_nodes, attacker_data.a_nodes)}

def greed_jaccard(attacker_data, threshold):
    a_nodes = attacker_data.a_nodes
    t_edge_map = graph.edge_map(attacker_data.target)
    a_edge_map = graph.edge_map(attacker_data.aux)
    def expand(node, edge_map):
        return set(islice(misc.breadth_first_walk(node, lambda n: edge_map[n]), 200))
    t_surround_map = {t: expand(t, t_edge_map) for t in attacker_data.t_nodes}
    a_surround_map = {a: expand(a, a_edge_map) for a in attacker_data.a_nodes}
    for t in attacker_data.t_nodes:
        converted_t_surround = {attacker_data.known_seeds.get(t, t) for t in t_surround_map[t]}
        j_indices = ((a, jaccard_index(converted_t_surround, a_surround_map[a])) for a in a_nodes)
        above_threshold = [(a, index) for a, index in j_indices if index > threshold]
        best = max(above_threshold, key=lambda x: x[1], default=(None, None))[0]
        for a in a_nodes:
            yield (t, a, a == best)

def threshold_predict(jaccard_indices, threshold):
    return [(t, a) for t, a, index in jaccard_indices if index > threshold]

def jaccard_experiment(attacker_data, known_percentage):
    (experiment_attacker_data, unknown_seeds) = forget_sample_seeds(attacker_data, 1 - known_percentage)
    solution_key = dict(unknown_seeds)
    t_unknown = [t for t, a in unknown_seeds]
    a_unknown = [a for t, a in unknown_seeds]
    solutions = {(t, a, solution_key[t] == a) for t, a in product(t_unknown, a_unknown)}
    return (solutions, pairwise_jaccard_indices(experiment_attacker_data, t_unknown, a_unknown))

def jaccard_threshold_predictor_experiment(attacker_data, known_percentage, threshold):
    (solutions, j_indices) = jaccard_experiment(attacker_data, known_percentage)
    return (solutions, [(t, a, j_index > threshold) for t, a, j_index in j_indices])

