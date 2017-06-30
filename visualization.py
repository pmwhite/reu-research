import graphviz as gv
import networkx as nx
import github
import twitter
import stack
import common
import sys
import sqlite3
import os

def save_network(graph, filename):
    nx.write_gml(graph, filename, stringizer=str)

def network(init, child_gen, parent_gen, transform_leaves, depth):
    graph = nx.DiGraph()
    searched = set()
    leaves = [init]
    for curr_depth in range(depth):
        print('=================================== depth', curr_depth)
        new_leaves = set()
        transformed_leaves = list(transform_leaves(leaves))
        leaf_count = len(transformed_leaves)
        for index, leaf in enumerate(transformed_leaves):
            print('|', ('=' * index).ljust(leaf_count), '|')
            searched.add(leaf)
            for child in child_gen(leaf): 
                # print(leaf, '->', child)
                new_leaves.add(child)
                graph.add_node(child, attr_dict=child.to_json())
                graph.add_edge(leaf, child)
            for parent in parent_gen(leaf): 
                # print(parent, '->', leaf)
                new_leaves.add(parent)
                graph.add_node(parent, attr_dict=parent.to_json())
                graph.add_edge(parent, leaf)
        leaves = new_leaves - searched
    return graph

def github_network(login, depth, conn):
    initial_user = github.User.gen_fetch_login(login, conn)
    def child_gen(user):
        for repo in user.repos(conn):
            print(repo)
            if not repo.is_fork:
                for contributor in repo.contributors(conn):
                    yield contributor
    def parent_gen(user): return []
    def transform_leaves(leaves): return leaves

    return network(initial_user, child_gen, parent_gen, transform_leaves, depth)

def twitter_network(screen_name, depth, conn):
    initial_user = twitter.User.fetch_single_screen_name(screen_name, conn)
    def child_gen(user): 
        for friend in user.friends(conn):
            yield friend
    def parent_gen(user): return []
    def transform_leaves(leaves):
        def key(f): return 
        sorted_leaves =  list(sorted(leaves, 
            key=lambda f: max(f.follower_count, f.following_count)))
        return sorted_leaves[0:100]
    return network(initial_user, child_gen, parent_gen, transform_leaves, depth)

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
    #g = twitter_network(sys.argv[1], depth=2, conn=conn) #stack_network(2449599, cursor, depth=2)
    #save_network(g, sys.argv[2])
    # get_three_networks('mwilliams', 23909, 'mwilliams', cursor)
    common_networks('outputs', conn)
