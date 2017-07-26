from itertools import islice, product, combinations, takewhile
from collections import deque, namedtuple
from visualization import GexfWritable
from network import walk_edges
import misc
import graph

DataSet = namedtuple('DataSet', 'target aux seeds root')
Scenario = namedtuple('Scenario', 't_walk a_walk seed_pred')

def union(dataset1, dataset2):
    return DataSet(
            target=graph.union(dataset1.target, dataset2.target),
            aux=graph.union(dataset1.aux, dataset2.aux),
            seeds=set.union(dataset1.seeds, dataset2.seeds),
            root=dataset1.root)

def singleton(seed):
    return DataSet(
            target=graph.singleton(seed[0]),
            aux=graph.singleton(seed[1]),
            seeds={seed},
            root=seed[0])

def breadth_first_seed_explore(initial_dataset, expander, quit_pred):
    result = initial_dataset
    def expand(seed):
        new_data = expander(seed)
        nonlocal result
        result = union(result, new_data)
        if quit_pred(result):
            return None
        else:
            return new_data.seeds
    for seed in misc.breadth_first_walk_from(result.seeds, expand):
        continue
    return result

def n_hop_seed_explore(initial_dataset, expander, n):
    result = initial_dataset
    def expand(seed):
        new_data = expander(seed)
        result = union(result, new_data)
        if quit_pred(result):
            return None
        else:
            return new_data.seeds
    for hop in islice(misc.hop_iter(result.seeds, expand), n):
        continue
    return result

def single_batch(initial_seed, scenario, batch_size):
    (t_seed, a_seed) = initial_seed
    t_graph = graph.pull_n_nodes(batch_size, walk_edges(t_seed, scenario.t_walk))
    a_graph = graph.pull_n_nodes(batch_size, walk_edges(a_seed, scenario.a_walk))
    seeds = set(graph.seed(t_graph, a_graph, scenario.seed_pred)) | {initial_seed}
    return DataSet(
            target=t_graph,
            aux=a_graph,
            seeds=seeds,
            root=t_seed)

def simple_batch_seed_cluster(initial_seed, scenario, cluster_size, batch_size):
    return breadth_first_seed_explore(
            initial_dataset=singleton(initial_seed),
            expander=lambda seed: single_batch(initial_seed, scenario, batch_size),
            quit_pred=lambda dataset: len(dataset.seeds) > cluster_size)

def hop_clustered_seed_search(initial_seed, scenario, cluster_size, batch_sizes):
    starting_cluster = simple_batch_seed_cluster(
            initial_seed, scenario, cluster_size, batch_sizes[0])
    return n_hop_seed_explore(
            initial_dataset=starting_cluster,
            expander=lambda seed: single_batch(initial_seed, scenario, batch_size),
            n=len(batch_sizes))

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
