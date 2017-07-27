from collections import namedtuple
from itertools import product, islice, chain
import itertools
import graph
import random
import misc
import table
from deanon import AttackerData

Experiment = namedtuple('Experiment', 'attacker_data solutions')

def cluster_partition(dataset, cluster_size):
    def expand(node):
        return set(islice(graph.surrounding_nodes(dataset.target, node), 500)).intersection(dataset.seeds)
    t_known_seeds = set(islice(misc.breadth_first_walk(dataset.root, expand), cluster_size))
    t_unknown_seeds = set()
    for t_known_seed in t_known_seeds:
        expanded = set(expand(t_known_seed))
        t_unknown_seeds.update(expanded - t_known_seeds)
    known_seeds = {t: dataset.seeds[t] for t in t_known_seeds}
    t_unknown = list(t_unknown_seeds)
    a_unknown = [dataset.seeds[t] for t in t_unknown]
    return Experiment(
            attacker_data=AttackerData(
                target=dataset.target,
                aux=dataset.aux,
                known_seeds=known_seeds,
                t_nodes=t_unknown,
                a_nodes=a_unknown),
            solutions={(t, dataset.seeds[t]) for t in t_unknown})

def random_partition(dataset, known_percentage):
    num_known = int(known_percentage * len(dataset.seeds))
    t_seeds = set(dataset.seeds)
    t_known = set(random.sample(t_seeds, num_known))
    t_unknown = list(t_seeds - t_known)
    a_unknown = [dataset.seeds[t] for t in t_unknown]
    return Experiment(
            attacker_data=AttackerData(
                target=dataset.target,
                aux=dataset.aux, 
                known_seeds={t: dataset.seeds[t] for t in t_known},
                t_nodes=t_unknown,
                a_nodes=a_unknown),
            solutions={(t, dataset.seeds[t]) for t in t_unknown})

def random_multicluster_partition(dataset, cluster_size, clusters):
    def expand(node):
        return set(islice(graph.surrounding_nodes(dataset.target, node), 500)).intersection(dataset.seeds)
    t_known_seeds = set()
    for cluster_root in random.sample(set(dataset.seeds), clusters):
        t_known_seeds.update(islice(misc.breadth_first_walk(cluster_root, expand), cluster_size))
    t_unknown_seeds = set()
    for t_known_seed in t_known_seeds:
        expanded = set(expand(t_known_seed))
        t_unknown_seeds.update(expanded - t_known_seeds)
    known_seeds = {t: dataset.seeds[t] for t in t_known_seeds}
    t_unknown = list(t_unknown_seeds)
    a_unknown = [dataset.seeds[t] for t in t_unknown]
    return Experiment(
            attacker_data=AttackerData(
                target=dataset.target,
                aux=dataset.aux,
                known_seeds=known_seeds,
                t_nodes=t_unknown,
                a_nodes=a_unknown),
            solutions={(t, dataset.seeds[t]) for t in t_unknown})

def concentrated_random_partition(dataset, cluster_size, known_percentage):
    def expand(node):
        return set(islice(graph.surrounding_nodes(dataset.target, node), 500)).intersection(dataset.seeds)
    t_seeds = set(islice(misc.breadth_first_walk(dataset.root, expand), cluster_size))
    num_known = int(known_percentage * len(t_seeds))
    t_known = set(random.sample(t_seeds, num_known))
    t_unknown = list(t_seeds - t_known)
    a_unknown = [dataset.seeds[t] for t in t_unknown]
    return Experiment(
            attacker_data=AttackerData(
                target=dataset.target,
                aux=dataset.aux, 
                known_seeds={t: dataset.seeds[t] for t in t_known},
                t_nodes=t_unknown,
                a_nodes=a_unknown),
            solutions={(t, dataset.seeds[t]) for t in t_unknown})

def evaluate_predictions(predictions, solutions):
    pred = set(predictions)
    sol = set(solutions)
    fp = len(pred - sol)
    tp = len(pred & sol)
    fn = len(sol - pred)
    print('correct:', tp, ', incorrect:', fp)
    if tp + fp == 0: 
        precision = 1
    else:
        precision = tp / (tp + fp)
    if tp + fn == 0:
        recall = 1
    else:
        recall = tp / (tp + fn)
    return (precision, recall)

def analyze(experiment, predictor):
    return evaluate_predictions(predictor(experiment.attacker_data), experiment.solutions)

def analyze_metrics(experiment, metric1, metric2):
    ad = experiment.attacker_data
    p_series = []
    n_series = []
    m1 = metric1(ad)
    m2 = metric2(ad)
    for t, a in product(ad.t_nodes, ad.a_nodes):
        item = (m1(t, a), m2(t, a))
        if (t, a) in experiment.solutions:
            p_series.append(item)
        else:
            n_series.append(item)
    return (p_series, n_series)

def analyze_rows(experiment, metric):
    ad = experiment.attacker_data
    p_series = []
    n_series = []
    m = metric(ad)
    for i, t in enumerate(ad.t_nodes):
        for a in ad.a_nodes:
            item = (m(t, a), i)
            if (t, a) in experiment.solutions:
                p_series.append(item)
            else:
                n_series.append(item)
    return (p_series, n_series)
