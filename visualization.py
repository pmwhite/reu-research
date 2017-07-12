import graphviz as gv
import networkx as nx
import twitter
import stack
import sys
import sqlite3
import os
import github
import common
import network

def get_three_networks(s_user, t_user, g_user, out_dir, conn):
    username = g_user.login
    print('=' * 80, username, '=' * 80)
    print('-' * 80, 'stackoverflow graph', '-' * 80)
    stack_file = out_dir + '/stack.gml'
    if not os.path.exists(stack_file):
        stack_graph = stack_network(s_user, depth=2, conn=conn)
        save_network(stack_graph, stack_file)
    else:
        print('file already exists')
    print('-' * 80, 'twitter graph', '-' * 80)
    twitter_file = out_dir + '/twitter.gml'
    if not os.path.exists(twitter_file):
        twitter_graph = twitter_network(t_user, depth=2, conn=conn)
        save_network(twitter_graph, twitter_file)
    else:
        print('file already exists')
    print('-' * 80, 'github graph', '-' * 80)
    github_file = out_dir + '/github.gml'
    if not os.path.exists(github_file):
        github_graph = github_network(g_user, depth=2, conn=conn)
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
        get_three_networks(s_user, t_user, g_user, target_dir, conn)

with sqlite3.connect('data/data.db') as conn:
    # g = common_graphs(20, cursor)
    # g = twitter_network(sys.argv[1], depth=2, conn=conn) #stack_network(2449599, cursor, depth=2)
    # save_network(g, sys.argv[2])
    # get_three_networks('mwilliams', 23909, 'mwilliams', cursor)
    common_networks('outputs', conn)
