from itertools import islice, product, combinations
from visualization import GexfWritable
from network import walk_edges
from collections import namedtuple
import random
import misc
import graph
from collections import deque, namedtuple

DataSet = namedtuple('DataSet', 'target aux seeds root')

def graph_seeds(target, aux, pred):
    pairs = product(target.nodes.values(), aux.nodes.values())
    return {(t, a) for t, a in pairs if pred(t, a)}

def closest_seeds(target_root, aux_root, target_walk, aux_walk, seed_pred, batch_size, conn):
    def expand(seed):
        (t, a) = seed
        t_explore = graph.pull_n_nodes(batch_size, walk_edges(t, target_walk, conn))
        a_explore = graph.pull_n_nodes(batch_size, walk_edges(a, aux_walk, conn))
        return graph_seeds(t_explore, a_explore, seed_pred)
    return misc.breadth_first_walk((target_root, aux_root), expand)

def n_hop_clustered_seed_search(
        target_root, aux_root, target_walk, aux_walk, 
        seed_pred, n, cluster_size, conn):
    target_graph = graph.empty_graph()
    aux_graph = graph.empty_graph()
    seeds = set(islice(closest_seeds(target_root, aux_root, target_walk, aux_walk, seed_pred, 500, conn), cluster_size))
    leaves = seeds
    for batch_size in [500, 200]:
        new_leaves = set()
        for seed_target, seed_aux in misc.progress_list(list(leaves)):
            target_exploration = graph.pull_n_nodes(batch_size, walk_edges(seed_target, target_walk, conn))
            aux_exploration = graph.pull_n_nodes(batch_size, walk_edges(seed_aux, aux_walk, conn))
            new_seeds = graph_seeds(target_exploration, aux_exploration, seed_pred)
            new_leaves = new_leaves | new_seeds
            target_graph = graph.union(target_graph, target_exploration)
            aux_graph = graph.union(aux_graph, aux_exploration)
            print('seeds:', len(seeds), 'target nodes:', len(target_graph.nodes), 'auxiliary nodes:', len(aux_graph.nodes))
        leaves = new_leaves - seeds
        seeds = seeds | leaves
    return DataSet(
            target=target_graph, 
            aux=aux_graph, 
            seeds={misc.hash(t): misc.hash(a) for t, a in seeds},
            root=misc.hash(target_root))

def breadth_first_seed_search(
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
    return DataSet(
            target=target_graph, 
            aux=aux_graph, 
            seeds={misc.hash(t): misc.hash(a) for t, a in seeds},
            root=misc.hash(target_root))

def mash_dataset(dataset):
    return graph.mash(
            dataset.target,
            dataset.aux,
            dataset.seeds.items(),
            lambda t, a: (t, a))

def mashed_gexf(target_gexf, aux_gexf, target_name="target", aux_name="aux"):
    t_prefix = target_name + '_'
    a_prefix = aux_name + '_'
    schema = {'node_type': 'string', 
            **misc.prefix_keys(target_gexf.schema, t_prefix),
            **misc.prefix_keys(aux_gexf.schema, a_prefix)}
    def serialize(mashed):
        (t, a) = mashed
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
    def label(mashed):
        (t, a) = mashed
        if t is not None:
            return target_gexf.label(t)
        else:
            return aux_gexf.label(a)
    return GexfWritable(
            schema=schema,
            serialize=serialize,
            label=label)
