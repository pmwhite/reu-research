from itertools import islice, product, combinations, takewhile
import itertools
from visualization import GexfWritable
from network import walk_edges
from collections import namedtuple
import random
import misc
import graph
from collections import deque, namedtuple

DataSet = namedtuple('DataSet', 'target aux seeds root')

def closest_seeds(initial_seed, target_walk, aux_walk, seed_pred, batch_size, conn):
    def expand(seed):
        (t, a) = seed
        t_explore = graph.pull_n_nodes(batch_size, walk_edges(t, target_walk, conn))
        a_explore = graph.pull_n_nodes(batch_size, walk_edges(a, aux_walk, conn))
        return graph.seed(t_explore, a_explore, seed_pred)
    return misc.breadth_first_walk(initial_seed, expand)

def n_hop_clustered_seed_search(
        initial_seed, t_walk, a_walk, 
        seed_pred, cluster_size, conn):
    t_graph = graph.empty_graph()
    a_graph = graph.empty_graph()
    seeds = set(islice(closest_seeds(initial_seed, t_walk, a_walk, seed_pred, 500, conn), cluster_size))
    leaves = seeds
    for batch_size in [500, 200]:
        new_leaves = set()
        for seed_t, seed_a in misc.progress_list(list(leaves)):
            t_explore = graph.pull_n_nodes(batch_size, walk_edges(seed_t, t_walk, conn))
            a_explore = graph.pull_n_nodes(batch_size, walk_edges(seed_a, a_walk, conn))
            new_seeds = graph.seed(t_explore, a_explore, seed_pred)
            new_leaves.update(new_seeds)
            t_graph = graph.union(t_graph, t_explore)
            a_graph = graph.union(a_graph, a_explore)
            print('seeds:', len(seeds), 'target nodes:', len(t_graph), 'auxiliary nodes:', len(a_graph))
        leaves = new_leaves - seeds
        seeds = seeds | leaves
    return DataSet(
            target=t_graph, 
            aux=a_graph, 
            seeds=dict(seeds),
            root=initial_seed[0])

def breadth_first_seed_search(
        initial_seed, t_walk, a_walk,
        seed_pred, max_seeds, max_nodes, batch_size, conn):
    search_queue = deque()
    search_queue.append(initial_seed)
    t_graph = graph.empty_graph()
    a_graph = graph.empty_graph()
    total_seeds = 0
    def expand(node):
        (t_seed, a_seed) = node
        t_explore = graph.pull_n_nodes(batch_size, walk_edges(t_seed, t_walk, conn))
        a_explore = graph.pull_n_nodes(batch_size, walk_edges(a_seed, a_walk, conn))
        t_graph = graph.union(t_graph, t_explore)
        a_graph = graph.union(a_graph, a_explore)
        seeds = list(graph.seed(t_explore, a_explore, seed_pred))
        total_seeds += len(seeds)
        print('seeds:', total_seeds, 'target nodes:', len(t_graph), 'auxiliary nodes:', len(a_graph))
        if total_seeds > max_seeds or len(t_graph) > max_nodes or len(a_graph) > max_nodes:
            return []
        return seeds
    seeds = set(misc.breadth_first_walk(initial_seed, expand))
    return DataSet(
            target=t_graph, 
            aux=a_graph, 
            seeds=dict(seeds),
            root=initial_seed[0])

def mash_dataset(dataset):
    return graph.zip_with(
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
        print(mashed)
        (t, a) = mashed
        if t is not None:
            return target_gexf.label(t)
        else:
            return aux_gexf.label(a)
    return GexfWritable(
            schema=schema,
            serialize=serialize,
            label=label)
