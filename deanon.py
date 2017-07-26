from itertools import islice, product
from collections import namedtuple
import graph
import table

AttackerData = namedtuple('AttackerData', 'target aux known_seeds t_nodes a_nodes')

def jaccard_index(s1, s2):
    return len(s1 & s2) / len(s1 | s2)

def jaccard_string_index(str1, str2):
    return jaccard_index(set(str1), set(str2))

def pairwise_metric_greedy(attacker_data, metric, threshold):
    m_table = table.table_apply(
            attacker_data.t_nodes, attacker_data.a_nodes, metric(attacker_data))
    a_nodes = attacker_data.a_nodes
    for t in attacker_data.t_nodes:
        indices = ((a, table.index(m_table, t, a)) for a in a_nodes)
        above_threshold = [(a, index) for a, index in indices if index > threshold]
        best = max(above_threshold, key=lambda x: x[1], default=(None, None))[0]
        for a in a_nodes:
            yield (t, a, a == best)

def pairwise_metric_conservative(attacker_data, metric, threshold):
    m_table = table.table_apply(
            attacker_data.t_nodes, attacker_data.a_nodes, metric(attacker_data))
    a_nodes = attacker_data.a_nodes
    for t in attacker_data.t_nodes:
        indices = ((a, table.index(m_table, t, a)) for a in a_nodes)
        above_threshold = [(a, index) for a, index in indices if index > threshold]
        if len(above_threshold) == 1:
            best = max(above_threshold, key=lambda x: x[1], default=(None, None))[0]
            for a in a_nodes:
                yield (t, a, a == best)
        else:
            for a in a_nodes:
                yield (t, a, False)

def pairwise_metric_simple_threshold(attacker_data, metric, threshold):
    m_table = table.table_apply(
            attacker_data.t_nodes, attacker_data.a_nodes, metric(attacker_data))
    return [(t, a, table.index(m_table, t, a) > threshold) 
        for t, a in product(attacker_data.t_nodes, attacker_data.a_nodes)]

def pairwise_metric_best_n_match(attacker_data, metric, n):
    m_table = table.table_apply(
            attacker_data.t_nodes, attacker_data.a_nodes, metric(attacker_data))
    metric_sort = sorted(product(attacker_data.t_nodes, attacker_data.a_nodes), 
            key=lambda pair: table.index(m_table, pair[0], pair[1]),
            reverse=True)
    if len(metric_sort) is not None:
        for t_best, a_best in metric_sort[0:n]:
            print(t_best.location, '|', a_best.location)
            yield (t_best, a_best, True)
        for t, a in metric_sort[n:]:
            yield (t, a, False)

def seed_distances_metric(attacker_data):
    converted_t_dists = {attacker_data.known_seeds[t]: graph.distances(attacker_data.target, t, attacker_data.known_seeds) 
            for t in attacker_data.t_nodes}
    a_dists_map = {a: graph.distances(attacker_data.aux, a, attacker_data.known_seeds.values()) 
            for a in attacker_data.a_nodes}
    def metric(t, a):
        t_dists = t_dists_map[t]
        a_dists = a_dists_map[a]
        result = sum(abs(converted_t_dists[a_seed] - a_dist) for a_seed, a_dist in a_dists.items())
        return 30 - result
    return metric

def jaccard_metric(attacker_data):
    def surrounding_nodes(node, g):
        return g[node]
        return set(islice(graph.surrounding_nodes(g, node), 50))
    converted_t_sets = {
        t: {attacker_data.known_seeds.get(x, x) 
            for x in surrounding_nodes(t, attacker_data.target)}
        for t in attacker_data.t_nodes}
    a_sets = {a: surrounding_nodes(a, attacker_data.aux) for a in attacker_data.a_nodes}
    return lambda t, a: jaccard_index(converted_t_sets[t], a_sets[a])

def location_metric(attacker_data):
    def metric(t, a):
        if t.location is not None and a.location is not None:
            return jaccard_string_index(t.location, a.location)
        else:
            return 0
    return metric

def jaccard_location_metric(attacker_data):
    j_metric = jaccard_metric(attacker_data)
    l_metric = location_metric(attacker_data)
    return lambda t, a: j_metric(t, a) + l_metric(t, a)
