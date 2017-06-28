import graphviz as gv
import networkx as nx
import github
import twitter
import stack
import sys
import sqlite3

def save_network(graph, filename):
    nx.write_gml(graph, filename, stringizer=str)

def network(init, child_gen, parent_gen, depth):
    graph = nx.DiGraph()
    searched = set()
    leaves = [init]
    for curr_depth in range(depth):
        print('=================================== depth', curr_depth)
        new_leaves = set()
        leaf_count = len(leaves)
        for index, leaf in enumerate(leaves):
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

def github_network(login, depth, cursor):
    initial_user = github.User.fetch_login(login, cursor)
    def child_gen(user):
        for repo in user.repos(cursor):
            if not repo.is_fork:
                print(repo)
                for contributor in repo.contributors(cursor):
                    yield contributor

    def parent_gen(user): return []

    return network(initial_user, child_gen, parent_gen, depth)

def twitter_network(screen_name, depth, conn):
    initial_user = twitter.User.fetch_single_screen_name(screen_name, conn)

    def child_gen(user): 
        for friend in user.friends(conn):
            if friend.follower_count < 20000 and friend.following_count < 20000:
                yield friend

    def parent_gen(user): return []

    return network(initial_user, child_gen, parent_gen, depth)

def stack_network(user_id, cursor, depth):
    initial_user = stack.User.fetch_id(user_id, cursor)
    def child_gen(user): return user.questioners(cursor)
    def parent_gen(user): return user.answerers(cursor)

    return network(initial_user, child_gen, parent_gen, depth)


def get_three_networks(username, stack_id, out_dir, cursor):
    print('==========', username, '==========')
    print('---------- stackoverflow graph ----------')
    stack_graph = stack_network(stack_id, cursor, depth=2)
    save_network(stack_graph, out_dir + '/stack.gml')
    print('---------- twitter graph ----------')
    twitter_graph = twitter_network(username, depth=2)
    save_network(twitter_graph, out_dir + '/twitter.gml')
    print('---------- github graph ----------')
    github_graph = github_network(username, depth=2)
    save_network(github_graph, out_dir + '/github.gml')


def common_networks(n, cursor):
    common_users = cursor.execute('''
        SELECT gtu.Login, su.Id FROM GithubTwitterUsers gtu
        JOIN StackUsers su ON gtu.Login = su.DisplayName
        WHERE su.Location = gtu.Location''').fetchmany(n)

    print('fetched')

    for (common_username, stack_id) in common_users:
        get_three_networks
    

with sqlite3.connect('data/data.db') as conn:
    cursor = conn.cursor()
    # g = common_graphs(20, cursor)
    g = twitter_network(sys.argv[1], depth=2, conn=conn) #stack_network(2449599, cursor, depth=2)
    save_network(g, sys.argv[2])
    # get_three_networks('mwilliams', 23909, 'mwilliams', cursor)
