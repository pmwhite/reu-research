import graphviz as gv
import networkx as nx
import twitter
import stack
import sys
import sqlite3
import os
import github

def save_network(graph, filename):
    nx.write_gml(graph, filename, stringizer=str)

def network(init, child_gen, parent_gen, transform_leaves, serialize, depth):
    graph = nx.DiGraph()
    searched = set()
    leaves = [init]
    for curr_depth in range(depth):
        print('=================================== depth', curr_depth)
        new_leaves = set()
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
        return sorted_leaves[0:100]
    return network(initial_user, child_gen, parent_gen, transform_leaves, twitter.user_to_json, depth)

def stack_network(user_id, depth, conn):
    initial_user = stack.User.fetch_id(user_id, conn)
    def child_gen(user): return user.questioners(conn)
    def parent_gen(user): return user.answerers(conn)
    def transform_leaves(leaves): return leaves
    return network(initial_user, child_gen, parent_gen, transform_leaves, depth)


def get_three_networks(username, stack_id, out_dir, onn):
    print('==========', username, '==========')
    os.mkdir(out_dir)
    print('---------- stackoverflow graph ----------', stack_id)
    stack_graph = stack_network(stack_id, depth=2, conn=conn)
    save_network(stack_graph, out_dir + '/stack.gml')
    print('---------- twitter graph ----------')
    twitter_graph = twitter_network(username, depth=2, conn=conn)
    save_network(twitter_graph, out_dir + '/twitter.gml')
    print('---------- github graph ----------')
    github_graph = github_network(username, depth=2, conn=conn)
    save_network(github_graph, out_dir + '/github.gml')


def common_networks(out_dir, conn):
    os.mkdir(out_dir)
    for (github_user, twitter_user, stack_users) in common.find_common_users(conn):
        if len(stack_users) == 1:
            get_three_networks(github_user.login, stack_users[0].user_id, out_dir + '/' + github_user.login, conn)


    

with sqlite3.connect('data/data.db') as conn:
    # g = common_graphs(20, cursor)
    g = twitter_network(sys.argv[1], depth=2, conn=conn) #stack_network(2449599, cursor, depth=2)
    save_network(g, sys.argv[2])
    # get_three_networks('mwilliams', 23909, 'mwilliams', cursor)
    # common_networks('outputs', conn)
