import graphviz as gv
import networkx as nx
import twitter
import stack
import github
import sqlite3
from collections import namedtuple

Network = namedtuple('Network', 'init child_gen parent_gen transform_leaves serialize')

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

def root_degree(network, conn):
    out_degree = len(list(children(network, conn)))
    in_degree = len(list(parents(network, conn)))
    return out_degree + in_degree

def children(network, conn):
    return network[1](network[0], conn)

def parents(network, conn):
    return network[2](network[0], conn)

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
