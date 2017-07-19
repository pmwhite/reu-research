from itertools import islice, product, combinations
from collections import deque, namedtuple
from visualization import NodeVisualizer
from network import walk_edges
import misc
import graph

AttackerData = namedtuple('AttackerData', 'target aux seeds')
CombinedNode = namedtuple('CombinedNode', 'target aux')

def graph_seeds(target, aux, pred):
    pairs = product(target.nodes.values(), aux.nodes.values())
    return {CombinedNode(t, a) for t, a in pairs if pred(t, a)}

def collect_attacker_data(
        target_root, aux_root, target_walk, aux_walk, 
        seed_pred, max_seeds, max_nodes, batch_size, conn):
    search_queue = deque()
    initial_seed = CombinedNode(target_root, aux_root)
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

def mash_attacker_data(attacker_data):
    return graph.mash(
            attacker_data.target,
            attacker_data.aux,
            attacker_data.seeds,
            lambda t, a: CombinedNode(t, a))

def mashed_visualizer(target_vis, aux_vis, target_name="target", aux_name="aux"):
    t_prefix = target_name + '_'
    a_prefix = aux_name + '_'
    schema = {'node_type': 'string', 
            **misc.prefix_keys(target_vis.schema, t_prefix),
            **misc.prefix_keys(aux_vis.schema, a_prefix)}
    def serialize(combined_node):
        (t, a) = combined_node
        if t is not None and a is not None:
            return {'node_type': target_name + '_' + aux_name, 
                    **misc.prefix_keys(target_vis.serialize(t), t_prefix),
                    **misc.prefix_keys(aux_vis.serialize(a), a_prefix)}
        elif t is not None:
            return {'node_type': target_name, 
                    **misc.prefix_keys(target_vis.serialize(t), t_prefix)}
        else:
            return {'node_type': aux_name, 
                    **misc.prefix_keys(aux_vis.serialize(a), a_prefix)}
    def label(combined_node):
        (t, a) = combined_node
        if t is not None:
            return target_vis.label(t)
        else:
            return aux_vis.label(a)
    return NodeVisualizer(
            schema=schema,
            serialize=serialize,
            label=label)
