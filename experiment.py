from collections import namedtuple
from itertools import product, islice, chain
import itertools
import graph
import misc
from deanon import AttackerData

Experiment = namedtuple('Experiment', 'attacker_data solutions')

def cluster_partition(dataset, cluster_size):
    t_edge_map = graph.edge_map(dataset.target)
    def expand(node):
        surrounding_nodes = set(islice(misc.breadth_first_walk(node, lambda n: t_edge_map[n]), 500))
        result = surrounding_nodes.intersection(dataset.seeds)
        return result
    t_known_seeds = set(islice(misc.breadth_first_walk(dataset.root, expand), cluster_size))
    t_unknown_seeds = set()
    for t_known_seed in t_known_seeds:
        expanded = set(expand(t_known_seed))
        for seed in expanded:
            if seed not in t_known_seeds:
                t_unknown_seeds.add(seed)
    known_seeds = {t: dataset.seeds[t] for t in t_known_seeds}
    t_nodes = t_unknown_seeds
    a_nodes = {dataset.seeds[t] for t in t_nodes}
    print(len(t_nodes))
    return Experiment(
            attacker_data=AttackerData(
                target=dataset.target,
                aux=dataset.aux,
                known_seeds=known_seeds,
                t_nodes=t_nodes,
                a_nodes=a_nodes),
            solutions={(t, a, dataset.seeds[t] == a) for t, a in product(t_nodes, a_nodes)})

def random_partition(dataset, known_percentage):
    num_known = int(percentage * len(attacker_data.seeds))
    t_seeds = set(dataset.seeds)
    t_known = set(random.sample(t_seeds, num_known))
    t_unknown = t_seeds - t_known
    a_unknown = {dataset.seeds[t] for t in t_unknown}
    return Experiment(
            attacker_data=AttackerData(
                target=dataset.target,
                aux=dataset.aux, 
                known_seeds={t: dataset.seeds[t] for t in t_known},
                t_nodes=t_unknown,
                a_nodes=a_unknown),
            solutions={(t, a, dataset.seeds[t] == a) for t, a in product(t_unknown, a_unknown)})

def evaluate_predictions(predictions, solutions):
    positives = {(t, a) for t, a, truth in predictions if truth}
    negatives = {(t, a) for t, a, truth in predictions if not truth}
    trues = {(t, a) for t, a, truth in solutions if truth}
    falses = {(t, a) for t, a, truth in solutions if not truth}
    fp = len(falses & positives)
    tn = len(trues & negatives)
    tp = len(trues & positives)
    print('correct:', tp)
    fn = len(falses & negatives)
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
