import graph
from network import walk_edges
from itertools import product
from collections import deque, namedtuple

AttackerData = namedtuple('AttackerData', 'target aux seeds')
Seed = namedtuple('Seed', 'target aux')

def graph_seeds(target, aux, pred):
    pairs = product(target.nodes.values(), aux.nodes.values())
    return {Seed(t, a) for t, a in pairs if pred(t, a)}

def collect_attacker_data(
        target_root, aux_root, target_walk, aux_walk, 
        seed_pred, max_seeds, max_nodes, batch_size, conn):
    search_queue = deque()
    initial_seed = Seed(target_root, aux_root)
    search_queue.append(initial_seed)
    target_graph = graph.empty_graph()
    aux_graph = graph.empty_graph()
    seeds = {initial_seed}
    while len(search_queue) != 0 and len(seeds) < max_seeds and len(target_graph.nodes) < max_nodes and len(aux_graph.nodes) < max_nodes:
        next_seed = search_queue.popleft()
        target_exploration = graph.pull_n_nodes(batch_size, walk_edges(next_seed.target, target_walk, conn))
        aux_exploration = graph.pull_n_nodes(batch_size, walk_edges(next_seed.aux, aux_walk, conn))
        new_seeds = graph_seeds(target_exploration, aux_exploration, seed_pred)
        print('found:', new_seeds)
        for seed in new_seeds:
            if seed not in seeds:
                search_queue.append(seed)
                seeds.add(seed)
        target_graph = graph.union(target_graph, target_exploration)
        aux_graph = graph.union(aux_graph, aux_exploration)
        print('seeds:', len(seeds), 'target nodes:', len(target_graph.nodes), 'auxiliary nodes:', len(aux_graph.nodes))
    return AttackerData(target_graph, aux_graph, seeds)
