import graphviz as gv
import networkx as nx
import twitter
import stack
import sys
import sqlite3
import os
import github
import common

def save_network(graph, filename):
    nx.write_gml(graph, filename, stringizer=str)

def network(init, child_gen, parent_gen, transform_leaves, serialize, depth):
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

def github_network(login, depth, conn):
    initial_user = github.user_fetch_login(login, conn)
    def child_gen(user):
        for repo in github.user_repos(user, conn):
            print(repo)
            if not repo.is_fork:
                for contributor in github.repo_contributors(repo, conn):
                    yield contributor
    def parent_gen(user):
        for repo in github.user_contributed_repos(user, conn):
            print(repo)
            yield github.user_fetch_login(repo.owner_login, conn)
    def transform_leaves(leaves): 
        for leaf in leaves:
            if leaf.login == 'Try-Git':
                continue
            else: 
                yield leaf
    return network(initial_user, child_gen, parent_gen, transform_leaves, github.user_to_json, depth)

def twitter_network(screen_name, depth, conn):
    initial_user = twitter.user_fetch_screen_name(screen_name, conn)
    def child_gen(user): 
        for friend in twitter.user_friends(user, conn):
            yield friend
    def parent_gen(user): return []
    def transform_leaves(leaves):
        sorted_leaves =  list(sorted(leaves, 
            key=lambda f: max(f.follower_count, f.following_count)))
        midpoint = int(len(sorted_leaves) / 2)
        s = max(midpoint - 25, 0)
        e = max(midpoint + 25, len(sorted_leaves))
        return sorted_leaves[s:e]
    return network(initial_user, child_gen, parent_gen, transform_leaves, twitter.user_to_json, depth)

def stack_network(user_id, depth, conn):
    initial_user = stack.User.fetch_id(user_id, conn)
    def child_gen(user): return user.questioners(conn)
    def parent_gen(user): return user.answerers(conn)
    def transform_leaves(leaves): return leaves
    return network(initial_user, child_gen, parent_gen, transform_leaves, stack.User.to_json, depth)

def get_three_networks(username, stack_id, out_dir, conn):
    print('=' * 80, username, '=' * 80)
    print('-' * 80, 'stackoverflow graph', '-' * 80)
    stack_file = out_dir + '/stack.gml'
    if not os.path.exists(stack_file):
        stack_graph = stack_network(stack_id, depth=2, conn=conn)
        save_network(stack_graph, stack_file)
    else:
        print('file already exists')
    print('-' * 80, 'twitter graph', '-' * 80)
    twitter_file = out_dir + '/twitter.gml'
    if not os.path.exists(twitter_file):
        twitter_graph = twitter_network(username, depth=2, conn=conn)
        save_network(twitter_graph, twitter_file)
    else:
        print('file already exists')
    print('-' * 80, 'github graph', '-' * 80)
    github_file = out_dir + '/github.gml'
    if not os.path.exists(github_file):
        github_graph = github_network(username, depth=2, conn=conn)
        save_network(github_graph, github_file)
    else:
        print('file already exists')

def common_networks(out_dir, conn):
    if not os.path.isdir(out_dir):
        os.mkdir(out_dir)
    for (s_user, t_user, g_user) in common.filtered(conn):
        target_dir = out_dir + '/' + g_user.login
        if not os.path.exists(target_dir):
            os.mkdir(target_dir)
        get_three_networks(g_user.login, s_user.user_id, target_dir, conn)

with sqlite3.connect('data/data.db') as conn:
    # g = common_graphs(20, cursor)
    # g = twitter_network(sys.argv[1], depth=2, conn=conn) #stack_network(2449599, cursor, depth=2)
    # save_network(g, sys.argv[2])
    # get_three_networks('mwilliams', 23909, 'mwilliams', cursor)
    common_networks('outputs', conn)
