import graphviz as gv
import networkx as nx
import twitter
import stack
import github
import sqlite3
from collections import namedtuple
from itertools import islice, chain

Network = namedtuple('Network', 'init child_gen parent_gen transform_leaves serialize')
Walk = namedtuple('Walk', 'out_gen in_gen select_leaves')

def save_network(graph, filename):
    nx.write_gml(graph, filename, stringizer=str)

def realize_depth(network, depth, conn):
    (init, child_gen, parent_gen, transform_leaves, serialize) = network
    graph = nx.DiGraph()
    searched = set()
    graph.add_node(hash(init), attr_dict=serialize(init))
    leaves = [init]
    for curr_depth in range(depth):
        print('=================================== depth', curr_depth)
        new_leaves = set()
        print(leaves)
        transformed_leaves = list(transform_leaves(leaves))
        leaf_count = len(transformed_leaves)
        print('leaves',transformed_leaves)
        for index, leaf in enumerate(transformed_leaves):
            print('|', ('=' * index).ljust(leaf_count), '|')
            searched.add(leaf)
            for child in child_gen(leaf): 
                print(leaf, '->', child)
                new_leaves.add(child)
                child_hash = hash(child)
                leaf_hash = hash(leaf)
                graph.add_node(child_hash, attr_dict=serialize(child))
                graph.add_edge(leaf_hash, child_hash)
            for parent in parent_gen(leaf):
                print(parent, '->', leaf)
                new_leaves.add(parent)
                parent_hash = hash(parent)
                leaf_hash = hash(leaf)
                graph.add_node(parent_hash, attr_dict=serialize(parent))
                graph.add_edge(parent_hash, leaf_hash)
        leaves = new_leaves - searched
    return graph

def nodes_iter(net, conn):
    searched = set()
    leaves = [net.init]
    while len(leaves) != 0:
        new_leaves = set()
        for leaf in net.transform_leaves(leaves):
            searched.add(leaf)
            for child in net.child_gen(leaf, conn): 
                new_leaves.add(child)
                yield child
            for parent in net.parent_gen(leaf, conn):
                new_leaves.add(parent)
                yield parent
        leaves = new_leaves - searched

def walk_events(init, walk, conn):
    nodes = {init}
    leaves = {init}
    while len(leaves) != 0:
        new_leaves = set()
        for leaf in walk.select_leaves(leaves):
            for out_node in walk.out_gen(leaf, conn): 
                new_leaves.add(out_node)
                yield (leaf, out_node)
            for in_node in walk.in_gen(leaf, conn):
                new_leaves.add(in_node)
                yield (in_node, leaf)
        leaves = new_leaves - nodes
        nodes = nodes + leaves

def walk_edges(init, walk, conn):
    nodes = {init}
    leaves = {init}
    while len(leaves) != 0:
        new_leaves = set()
        for leaf in walk.select_leaves(leaves):
            for out_node in walk.out_gen(leaf, conn): 
                new_leaves.add(out_node)
                yield (leaf, out_node)
            for in_node in walk.in_gen(leaf, conn):
                new_leaves.add(in_node)
                yield (in_node, leaf)
        leaves = new_leaves - nodes
        nodes = nodes.union(leaves)

def github_out_gen(user, conn):
    for repo in github.user_contributed_repos(user, conn):
        yield github.user_fetch_login(repo.owner_login, conn)

def github_in_gen(user, conn):
    for repo in github.user_repos(user, conn):
        if not repo.is_fork:
            for contributor in github.repo_contributors(repo, conn):
                yield contributor

def github_select_leaves(leaves): 
    for leaf in leaves:
        if leaf.login == 'Try-Git':
            continue
        else: 
            yield leaf

github_walk = Walk(
        out_gen=github_out_gen,
        in_gen=github_in_gen,
        select_leaves=github_select_leaves)

def twitter_out_gen(user, conn):
    for friend in twitter.user_friends(user, conn):
        yield friend

def twitter_in_gen(user, conn): return []

def twitter_select_leaves(leaves):
    sorted_leaves =  list(sorted(leaves, 
        key=lambda f: max(f.follower_count, f.following_count)))
    midpoint = int(len(sorted_leaves) / 2)
    s = max(midpoint - 25, 0)
    e = max(midpoint + 25, len(sorted_leaves))
    return sorted_leaves[s:e]

twitter_walk = Walk(
        out_gen=twitter_out_gen,
        in_gen=twitter_in_gen,
        select_leaves=twitter_select_leaves)

def stack_out_gen(user, conn): return stack.user_questioners(user, conn)

def stack_in_gen(user, conn): return stack.user_answerers(user, conn)

def stack_select_leaves(leaves): return leaves

stack_walk = Walk(
        out_gen=stack_out_gen,
        in_gen=stack_in_gen,
        select_leaves=stack_select_leaves)

def connections(net, conn):
    return chain(
            net.child_gen(net.init, conn),
            net.parent_gen(net.init, conn))

def github_network(initial_user):
    def child_gen(user, conn):
        for repo in github.user_contributed_repos(user, conn):
            yield github.user_fetch_login(repo.owner_login, conn)
    def parent_gen(user, conn):
        for repo in github.user_repos(user, conn):
            if not repo.is_fork:
                for contributor in github.repo_contributors(repo, conn):
                    yield contributor
    def transform_leaves(leaves): 
        for leaf in leaves:
            if leaf.login == 'Try-Git':
                continue
            else: 
                yield leaf
    return Network(
            init=initial_user,
            child_gen=child_gen,
            parent_gen=parent_gen,
            transform_leaves=transform_leaves,
            serialize=github.user_to_json)

def twitter_network(initial_user):
    def child_gen(user, conn): 
        for friend in twitter.user_friends(user, conn):
            yield friend
    def parent_gen(user, conn): return []
    def transform_leaves(leaves):
        sorted_leaves =  list(sorted(leaves, 
            key=lambda f: max(f.follower_count, f.following_count)))
        midpoint = int(len(sorted_leaves) / 2)
        s = max(midpoint - 25, 0)
        e = max(midpoint + 25, len(sorted_leaves))
        return sorted_leaves[s:e]
    return Network(
            init=initial_user,
            child_gen=child_gen,
            parent_gen=parent_gen,
            transform_leaves=transform_leaves,
            serialize=twitter.user_to_json)

def stack_network(initial_user):
    def child_gen(user, conn): return stack.user_questioners(user, conn)
    def parent_gen(user, conn): return stack.user_answerers(user, conn)
    def transform_leaves(leaves): return leaves
    return Network(
            init=initial_user,
            child_gen=child_gen,
            parent_gen=parent_gen,
            transform_leaves=transform_leaves,
            serialize=stack.user_to_json)
