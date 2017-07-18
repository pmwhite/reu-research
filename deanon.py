from itertools import islice, product, combinations
from collections import deque, namedtuple
import stack 
import github
import twitter
import misc
import graph
import network
import dataprep

def tg_pred(t_user, g_user):
    if g_user.login == t_user.screen_name:
        return True
    elif g_user.name is not None and t_user.name is not None and ' ' in g_user.name and g_user.name == t_user.name:
        return True
    else:
        return False

def seed_tg(t_user, g_user, seeds, nodes, batch_size, conn):
    return dataprep.collect_attacker_data(
            target_root=t_user, 
            aux_root=g_user,
            target_walk=network.twitter_walk,
            aux_walk=network.github_walk,
            seed_pred=tg_pred,
            max_seeds=seeds,
            max_nodes=nodes,
            batch_size=batch_size,
            conn=conn)

def prediction_groups(t_net, g_net, seeds, links):
    t_edge_map = graph.edge_map(t_net)
    g_edge_map = graph.edge_map(g_net)
    seed_hashes = {(misc.hash(tn), misc.hash(gn)) for tn, gn in seeds}
    for seed_group in combinations(seed_hashes, links):
        t_intersection = set.intersection(*(t_edge_map[th] for th, gh in seed_group))
        g_intersection = set.intersection(*(g_edge_map[gh] for th, gh in seed_group))
        t_nodes = {t_net.nodes[th] for th in t_intersection}
        g_nodes = {g_net.nodes[gh] for gh in g_intersection}
        yield (t_nodes, g_nodes)

def mash_tg(t, g):
    return (t, g)

def serialize_tg(tg):
    if type(tg) is github.User:
        return {**github.serialize_user(tg), 'node_type': 'g'}
    elif type(tg) is twitter.User:
        return {**twitter.serialize_user(tg), 'node_type': 't'}
    else:
        (t, g) = tg
        return {**twitter.serialize_user(t), **github.serialize_user(g), 'node_type': 'tg'}

tg_attribute_schema = {
        **twitter.user_attribute_schema, 
        **github.user_attribute_schema,
        'node_type': 'string'}

def label_tg(tg):
    if type(tg) is github.User: return tg.login
    elif type(tg) is twitter.User: return tg.screen_name
    else:
        print(tg)
        (t, g) = tg
        return g.login
