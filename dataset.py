"""This module contains functions for creating datasets. These functions are
for pulling data from some data source (maybe an API) and turning them into a
pair of graphs and some seeds."""
from itertools import islice, product, combinations, takewhile
from collections import deque, namedtuple
from visualization import GexfWritable
from network import walk_edges
import misc
import graph

DataSet = namedtuple('DataSet', 'target aux seeds root')
Scenario = namedtuple('Scenario', 't_walk a_walk seed_pred')

def union(dataset1, dataset2):
"Combines two datasets, keeping the root of the first."
    return DataSet(
            target=graph.union(dataset1.target, dataset2.target),
            aux=graph.union(dataset1.aux, dataset2.aux),
            seeds={**dataset1.seeds, **dataset2.seeds},
            root=dataset1.root)

def singleton(seed):
"Creates a dataset with one root seed node."
    (t, a) = seed
    return DataSet(
            target=graph.singleton(t),
            aux=graph.singleton(a),
            seeds={t: a},
            root=t)

def breadth_first_seed_explore(initial_dataset, expander, quit_pred):
"""Starting with an initial dataset, performs a 'breadth-first walk' with
respect to the seeds in the dataset. The behavior of this function is
controlled through the `expander` which takes a seed and returns an expanded
dataset."""
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
"""Starting with an initial dataset, performs a `n-hop search`, which means it
expands a hop at a time, rather than with a queue, as in breadth-first search.
The expander takes a seed and returns an expanded dataset."""
    result = initial_dataset
    def expand(seed):
        new_data = expander(seed)
        nonlocal result
        result = union(result, new_data)
        return new_data.seeds
    for hop in islice(misc.hop_iter(list(result.seeds), expand), n):
        continue
    return result

def single_batch(initial_seed, scenario, batch_size):
"""Creates a dataset from an initial seed with a certain amount of nodes in
both the target and auxiliary network. It takes a scenario, which describes how
the two networks can be traversed, and how they can be compared."""
    (t_seed, a_seed) = initial_seed
    t_graph = graph.pull_n_nodes(batch_size, walk_edges(t_seed, scenario.t_walk))
    a_graph = graph.pull_n_nodes(batch_size, walk_edges(a_seed, scenario.a_walk))
    seeds = {t_seed: a_seed, **dict(graph.seed(t_graph, a_graph, scenario.seed_pred))}
    return DataSet(
            target=t_graph,
            aux=a_graph,
            seeds=seeds,
            root=t_seed)

def simple_batch_seed_cluster(initial_seed, scenario, cluster_size, batch_size):
"""Creates a cluster of seeds surrounding an initial seed. It essentially
piggybacks off of `breadth_first_seed_explore`."""
    return breadth_first_seed_explore(
            initial_dataset=singleton(initial_seed),
            expander=lambda seed: single_batch(seed, scenario, batch_size),
            quit_pred=lambda dataset: len(dataset.seeds) > cluster_size)

def hop_clustered_seed_search(initial_seed, scenario, cluster_size, batch_sizes):
"""Currently isn't a great funtion. Go ahead and use it, but the parameters
don't make sense. It creates a dataset with the same number of hops as the
length of the batch_sizes parameter; it currently doesn't use all of these
batch_sizes. Instead, it creates a batch of size of the first item in the list,
and searches outward with batches of size of the second item in the list."""
    starting_cluster = simple_batch_seed_cluster(
            initial_seed, scenario, cluster_size, batch_sizes[0])
    result = n_hop_seed_explore(
            initial_dataset=starting_cluster,
            expander=lambda seed: single_batch(seed, scenario, batch_sizes[1]),
            n=len(batch_sizes))
    print(len(result.seeds))
    return result

def mash_dataset(dataset):
"""Useful for visualization. Combines two datasets in to one dataset which has
nodes as pairs."""
    return graph.zip_with(
            dataset.target,
            dataset.aux,
            dataset.seeds.items(),
            lambda t, a: (t, a))

def mashed_gexf(target_gexf, aux_gexf, target_name="target", aux_name="aux"):
"""Creates a function which can serialize a dataset which has been mashed
together."""
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
