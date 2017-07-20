from itertools import islice, product, combinations
from collections import deque, namedtuple
from visualization import GexfWritable
from network import walk_edges
import random
import misc
import graph

AttackerData = namedtuple('AttackerData', 'target aux seeds')
Table = namedtuple('Table', 'matrix columns rows')

def graph_seeds(target, aux, pred):
    pairs = product(target.nodes.values(), aux.nodes.values())
    return {(t, a) for t, a in pairs if pred(t, a)}

def collect_attacker_data(
        target_root, aux_root, target_walk, aux_walk, 
        seed_pred, max_seeds, max_nodes, batch_size, conn):
    search_queue = deque()
    initial_seed = (target_root, aux_root)
    search_queue.append(initial_seed)
    target_graph = graph.empty_graph()
    aux_graph = graph.empty_graph()
    seeds = {initial_seed}
    while len(search_queue) != 0 and len(seeds) < max_seeds and len(target_graph.nodes) < max_nodes and len(aux_graph.nodes) < max_nodes:
        (next_seed_target, next_seed_aux) = search_queue.popleft()
        target_exploration = graph.pull_n_nodes(batch_size, walk_edges(next_seed_target, target_walk, conn))
        aux_exploration = graph.pull_n_nodes(batch_size, walk_edges(next_seed_aux, aux_walk, conn))
        new_seeds = graph_seeds(target_exploration, aux_exploration, seed_pred)
        print('found:', new_seeds)
        for seed in new_seeds:
            if seed not in seeds:
                search_queue.append(seed)
                seeds.add(seed)
        target_graph = graph.union(target_graph, target_exploration)
        aux_graph = graph.union(aux_graph, aux_exploration)
        print('seeds:', len(seeds), 'target nodes:', len(target_graph.nodes), 'auxiliary nodes:', len(aux_graph.nodes))
    return AttackerData(
            target=target_graph, 
            aux=aux_graph, 
            seeds={(misc.hash(n1), misc.hash(n2)) for n1, n2 in seeds})

def prediction_groups(target_graph, aux_graph, seeds, links):
    t_edge_map = graph.edge_map(target_graph)
    a_edge_map = graph.edge_map(aux_graph)
    seed_hashes = {(misc.hash(tn), misc.hash(an)) for tn, an in seeds}
    for seed_group in combinations(seed_hashes, links):
        target_intersection = set.intersection(*(t_edge_map[th] for th, ah in seed_group))
        aux_intersection = set.intersection(*(a_edge_map[ah] for th, ah in seed_group))
        target_nodes = {target_graph.nodes[th] for th in target_intersection}
        aux_nodes = {aux_graph.nodes[gh] for ah in aux_intersection}
        yield (target_nodes, aux_nodes)

def jaccard_index(s1, s2):
    return len(s1 & s2) / len(s1 | s2)

def table_apply(items1, items2, f):
    return Table(
            matrix=[[f(item1, item2) for item2 in items2] for item1 in items1], 
            columns=items1, 
            rows=items2)

def pairwise_jaccard_indices(attacker_data, t_nodes, a_nodes):
    t_edge_map = graph.edge_map(attacker_data.target)
    a_edge_map = graph.edge_map(attacker_data.aux)
    t_to_a = {t: a for t, a in attacker_data.seeds}
    return [(t, a, jaccard_index({t_to_a.get(x, x) for x in t_edge_map[t]}, a_edge_map[a])) 
            for t, a in product(t_nodes, a_nodes)]

def threshold_predict(jaccard_indices, threshold):
    return [(t, a) for t, a, index in jaccard_indices if index > threshold]

def evaluate(predictions, solutions):
    positives = {(t, a) for t, a, truth in predictions if truth}
    negatives = {(t, a) for t, a, truth in predictions if not truth}
    trues = {(t, a) for t, a, truth in solutions if truth}
    falses = {(t, a) for t, a, truth in solutions if not truth}
    fp = len(falses & positives)
    tn = len(trues & negatives)
    tp = len(trues & positives)
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

def forget_sample_seeds(attacker_data, percentage):
    sample_size = int(percentage * len(attacker_data.seeds))
    sample = set(random.sample(attacker_data.seeds, sample_size))
    remaining_seeds = attacker_data.seeds - sample
    return (AttackerData(attacker_data.target, attacker_data.aux, remaining_seeds), sample)

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

def mash_attacker_data(attacker_data):
    return graph.mash(
            attacker_data.target,
            attacker_data.aux,
            attacker_data.seeds,
            lambda t, a: (t, a))

def mashed_gexf(target_gexf, aux_gexf, target_name="target", aux_name="aux"):
    t_prefix = target_name + '_'
    a_prefix = aux_name + '_'
    schema = {'node_type': 'string', 
            **misc.prefix_keys(target_gexf.schema, t_prefix),
            **misc.prefix_keys(aux_gexf.schema, a_prefix)}
    def serialize(combined_node):
        (t, a) = combined_node
        if t is not None and a is not None:
            return {'node_type': target_name + '_' + aux_name, 
                    **misc.prefix_keys(target_gexf.serialize(t), t_prefix),
                    **misc.prefix_keys(aux_gexf.serialize(a), a_prefix)}
        elif t is not None:
            return {'node_type': target_name, 
                    **misc.prefix_keys(target_gexf.serialize(t), t_prefix)}
        else:
            return {'node_type': aux_name, 
                    **misc.prefix_keys(aux_gexf.serialize(a), a_prefix)}
    def label(combined_node):
        (t, a) = combined_node
        if t is not None:
            return target_gexf.label(t)
        else:
            return aux_gexf.label(a)
    return GexfWritable(
            schema=schema,
            serialize=serialize,
            label=label)
