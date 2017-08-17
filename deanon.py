"""This module contains functions for de-anonymizing AttackerData objects. It
does not handle turning datasets into the objects; such a task is handled by
the `experiment` module. In this module, there are a few functions that are
categorized as 'metrics'. These functions take an `AttackerData` object, and
return a function which takes two users and returns a number. The initial call
is to allow the metric to cache any computation from the `AttackerData`
object."""

from itertools import islice, product
from collections import namedtuple
import graph
import table
from math import sqrt
import numpy

AttackerData = namedtuple('AttackerData', 'target aux known_seeds t_nodes a_nodes')

def jaccard_index(s1, s2):
"""Computes the Jaccard index for two sets, which is just the size of their
intersection divided by the size of their union."""
    return len(s1 & s2) / len(s1 | s2)

def cosine_jaccard_index(s1, s2):
"""A rather unscientific set similarity index. Supposed to be similar to cosine
similarity by removing the bias on larger sets."""
    return len(s1 & s2) / sqrt(len(s1 | s2))

def shared_fraction_max(s1, s2):
"""The fraction of the larger set's elements that are shared between the two
sets."""
    return len(s1 & s2) / max(len(s1), len(s2))

def shared_fraction_min(s1, s2):
"""The fraction of the smaller set's elements that are shared between the two
sets."""
    return len(s1 & s2) / min(len(s1), len(s2))

def cosine_similarity(seq1, seq2):
"""The cosine similarity between two lists. It is very similar to the
angle between the two lists if they are treated as vectors, but it ranges from 0 to 1."""
    l1 = list(seq1)
    l2 = list(seq2)
    dot = lambda v1, v2: sum(a * b for a, b in zip(v1, v2))
    vlen = lambda v: sqrt(dot(v, v))
    vlen1 = vlen(l1)
    vlen2 = vlen(l2)
    if vlen1 > 0 and vlen2 > 0:
        return dot(l1, l2) / (vlen(l1) * vlen(l2))
    else:
        return 0

def jaccard_string_index(str1, str2):
"""Applies the jaccard index to the set of characters in two strings. This is
not a scientific metric by any means, and it should probably be avoided."""
    return jaccard_index(set(str1), set(str2))

def metric_eccentricity_greedy(attacker_data, metric, ecc):
"""Predicts the pairs which have an eccentricity greater than a specified
amount for the given metric. This greedily predicts, which means that it only
selects the highest value for each target node. It does not take into account
later predictions."""
    m_table = table.table_apply(
            attacker_data.t_nodes, attacker_data.a_nodes, metric(attacker_data))
    a_nodes = attacker_data.a_nodes
    for t in attacker_data.t_nodes:
        indices = sorted(
                ((a, table.index(m_table, t, a)) for a in a_nodes),
                key=lambda x: x[1],
                reverse=True)
        if len(indices) == 1:
            yield (t, indices[0][0])
        elif len(indices) > 1:
            xs = [index for a, index in indices]
            eccentricity = (xs[0] - xs[1]) / numpy.std(xs)
            if eccentricity > ecc:
                yield (t, indices[0][0])

def pairwise_metric_greedy(attacker_data, metric, threshold):
"""Predicts the pairs which have an value greater than a specified
amount for the given metric. This greedily predicts, which means that it only
selects the highest value for each target node. It does not take into account
later predictions."""
    m_table = table.table_apply(
            attacker_data.t_nodes, attacker_data.a_nodes, metric(attacker_data))
    a_nodes = attacker_data.a_nodes
    for t in attacker_data.t_nodes:
        indices = ((a, table.index(m_table, t, a)) for a in a_nodes)
        above_threshold = [(a, index) for a, index in indices if index > threshold]
        best = max(above_threshold, key=lambda x: x[1], default=(None, None))[0]
        if best is not None:
            yield (t, best)

def pairwise_metric_conservative(attacker_data, metric, threshold):
"""Predicts only the pairs which have a value greater than the threshold for
the given metric, and also are the only ones to have values higher than the
metric."""
    m_table = table.table_apply(
            attacker_data.t_nodes, attacker_data.a_nodes, metric(attacker_data))
    a_nodes = attacker_data.a_nodes
    for t in attacker_data.t_nodes:
        indices = ((a, table.index(m_table, t, a)) for a in a_nodes)
        above_threshold = [(a, index) for a, index in indices if index > threshold]
        if len(above_threshold) == 1:
            best = max(above_threshold, key=lambda x: x[1], default=(None, None))[0]
            if best is not None:
                yield (t, best)

def pairwise_metric_simple_threshold(attacker_data, metric, threshold):
"""Predicts all pairs with a value greater than the specified threshold for the
given metric."""
    m_table = table.table_apply(
            attacker_data.t_nodes, attacker_data.a_nodes, metric(attacker_data))
    return [(t, a) for t, a in product(attacker_data.t_nodes, attacker_data.a_nodes)
        if table.index(m_table, t, a) > threshold]

def pairwise_metric_best_n_match(attacker_data, metric, n):
"""Predicts the pairs with the highest values according to the given metric."""
    m_table = table.table_apply(
            attacker_data.t_nodes, attacker_data.a_nodes, metric(attacker_data))
    metric_sort = sorted(product(attacker_data.t_nodes, attacker_data.a_nodes), 
            key=lambda pair: table.index(m_table, pair[0], pair[1]),
            reverse=True)
    if len(metric_sort) != 0:
        for t_best, a_best in metric_sort[0:n]:
            print(t_best.location, '|', a_best.location)
            yield (t_best, a_best)

def seed_distances_metric(attacker_data):
"""Compares distances from all the known nodes of the targets and potentials."""
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
"""Simple comparison of nodes based on the jaccard index of the connection
sets. The github nodes are converted to their corresponding twitter nodes if
possible to allow matching nodes to be equal."""
    def surrounding_nodes(node, g):
        return g[node]
        return set(islice(graph.surrounding_nodes(g, node), 50))
    converted_t_sets = {
        t: {attacker_data.known_seeds.get(x, x) 
            for x in surrounding_nodes(t, attacker_data.target)}
        for t in attacker_data.t_nodes}
    a_sets = {a: surrounding_nodes(a, attacker_data.aux) for a in attacker_data.a_nodes}
    return lambda t, a: jaccard_index(converted_t_sets[t], a_sets[a])

def cosine_jaccard_metric(attacker_data):
"""Simple comparison of nodes based on the cosine jaccard index of the connection
sets. The github nodes are converted to their corresponding twitter nodes if
possible to allow matching nodes to be equal."""
    def surrounding_nodes(node, g):
        return g[node]
        return set(islice(graph.surrounding_nodes(g, node), 50))
    converted_t_sets = {
        t: {attacker_data.known_seeds.get(x, x) 
            for x in surrounding_nodes(t, attacker_data.target)}
        for t in attacker_data.t_nodes}
    a_sets = {a: surrounding_nodes(a, attacker_data.aux) for a in attacker_data.a_nodes}
    return lambda t, a: cosine_jaccard_index(converted_t_sets[t], a_sets[a])

def shared_fraction_max_metric(attacker_data):
"""Simple comparison of nodes based on the shared fraction of the larger set of
the connection sets. The github nodes are converted to their corresponding
twitter nodes if possible to allow matching nodes to be equal."""
    def surrounding_nodes(node, g):
        return g[node]
        return set(islice(graph.surrounding_nodes(g, node), 50))
    converted_t_sets = {
        t: {attacker_data.known_seeds.get(x, x) 
            for x in surrounding_nodes(t, attacker_data.target)}
        for t in attacker_data.t_nodes}
    a_sets = {a: surrounding_nodes(a, attacker_data.aux) for a in attacker_data.a_nodes}
    return lambda t, a: shared_fraction_max(converted_t_sets[t], a_sets[a])

def shared_fraction_min_metric(attacker_data):
"""Simple comparison of nodes based on the shared fraction of the smaller set of
the connection sets. The github nodes are converted to their corresponding
twitter nodes if possible to allow matching nodes to be equal."""
    def surrounding_nodes(node, g):
        return g[node]
        return set(islice(graph.surrounding_nodes(g, node), 50))
    converted_t_sets = {
        t: {attacker_data.known_seeds.get(x, x) 
            for x in surrounding_nodes(t, attacker_data.target)}
        for t in attacker_data.t_nodes}
    a_sets = {a: surrounding_nodes(a, attacker_data.aux) for a in attacker_data.a_nodes}
    return lambda t, a: shared_fraction_min(converted_t_sets[t], a_sets[a])
