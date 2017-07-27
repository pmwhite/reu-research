from itertools import islice
from network import walk_edges
from visualization import write_gexf
import os
import argparse
import sqlite3
import pickle
import twitter
import github
import common
import graph
import deanon
import dataset

def stubborn(f):
    while True:
        try:
            f()
            break
        except Exception as e:
           print(e)

def main1():
    with sqlite3.connect('data/data.db') as conn:
        username = 'abidibo'
        g_user = github.user_fetch_login(username, conn)
        t_user = twitter.user_fetch_screen_name(username, conn)
        dset = dataset.simple_batch_seed_cluster((t_user, g_user), common.tg_scenario(conn), 10, 10000)
        write_gexf(dset.target, twitter.user_gexf).write('funfun/abidibo_main1.gexf')
        with open('funfun/abidibo_main1.pickle', 'wb') as f:
            pickle.dump(dset, f)


def run_stuff(conn):
    while True:
        try:
            for s_user, t_user, g_user in common.active_matches(20, 20, 8, conn):
                print('=' * 80, t_user.screen_name, '=' * 80)
                if not os.path.isfile('outputs/twitter_' + t_user.screen_name + '.gexf'):
                    (t_net, g_net, tg_seeds) = deanon.seed_tg(t_user, g_user, 20, conn)
                    mashed = graph.mash(t_net, g_net, tg_seeds, deanon.mash_tg)
                    graph.to_gexf(
                            mashed, 
                            deanon.tg_attribute_schema, 
                            deanon.serialize_tg, 
                            deanon.label_tg).write('outputs/mashed_' + t_user.screen_name + '.gexf')
                    graph.write_twitter(t_net, 'outputs/twitter_' + t_user.screen_name + '.gexf')
                    graph.write_github(g_net, 'outputs/github_' + t_user.screen_name + '.gexf')
                conn.commit()
        except Exception as e:
           print(e)

def deanon_triple(triple, conn):
    (s_user, t_user, g_user) = triple
    (t_net, g_net, tg_seeds) = deanon.seed_tg(t_user, g_user, 20, conn)
    for t_group, g_group in deanon.prediction_groups(t_net, g_net, tg_seeds, 3):
        if len(t_group) != 0 and len(g_group) != 0:
            print('=' * 30)
            for user in t_group: print(user)
            print()
            for user in g_group: print(user)
            print()

def list_matches(conn, after, amount=20):
    for s_users, t_user, g_user in islice(common.username_matches(conn, after=after), amount):
        print('=' * 20)
        for user in s_users:
            print(user)
        print(t_user)
        print(g_user)
        print()

def list_unique(conn, after, amount=20):
    for s_user, t_user, g_user in islice(common.unique_username_matches(conn, after=after), amount):
        print(s_user)
        print(t_user)
        print(g_user)
        print()

def list_active(conn, after, s_limit, t_limit, g_limit, amount):
    for s_user, t_user, g_user in islice(
            common.active_unique_username_matches(
                conn, s_limit, t_limit, g_limit, after=after), amount):
        print(s_user.display_name, t_user.screen_name, g_user.login)

def check_user(conn, username):
    (s_users, t_user, g_user) = common.check_username(username, conn)
    print('=' * 20)
    for user in s_users: print(user)
    if t_user is not None: print(t_user)
    if g_user is not None: print(g_user)
    print()

def pull_username_graph(conn, username, do_stack, do_twitter, do_github, nodes, out_dir):
    base_path = out_dir + '/' + username
    if do_stack:
        users = stack.user_fetch_display_name_all(username, conn)
        if len(users) == 1:
            g = graph.pull_n_nodes(nodes, walk_edges(users[0], stack.user_walk, conn))
            write_gexf(g, stack.user_gexf).write(base_path + '_stack.gexf')
        elif len(users) == 0:
            print('Stack user does not exist')
        else:
            print('Stack user not unique -', len(users), 'total')
    if do_twitter:
        user = twitter.user_fetch_screen_name(username, conn)
        if user is not None:
            g = graph.pull_n_nodes(nodes, walk_edges(user, twitter.user_walk, conn))
            write_gexf(g, twitter.user_gexf).write(base_path + '_twitter.gexf')
        else:
            print('Twitter user does not exist')
    if do_github:
        user = github.user_fetch_login(username, conn)
        if user is not None:
            g = graph.pull_n_nodes(nodes, walk_edges(user, github.user_walk, conn))
            write_gexf(g, github.user_gexf).write(base_path + '_github.gexf')
        else:
            print('Github user does not exist')

def deanon_user(conn, username, seeds, nodes, batch, out_dir):
    g_user = github.user_fetch_login(username, conn)
    t_user = twitter.user_fetch_screen_name(username, conn)
    print(t_user)
    print(g_user)
    if g_user and t_user:
        base_path = out_dir + username
        while True:
            try:
                attacker_data = common.tg_3_hop_seeds(t_user, g_user, batch, conn)
                mashed = dataset.mash_dataset(attacker_data)
                write_gexf(mashed, common.tg_gexf).write(base_path + '_mash.gexf')
                write_gexf(attacker_data.target, twitter.user_gexf).write(base_path + '_twitter.gexf')
                write_gexf(attacker_data.aux, github.user_gexf).write(base_path + '_github.gexf')
                with open(base_path + '_attack.pickle', 'wb') as f:
                    pickle.dump(attacker_data, f)
                break
            except Exception as e:
                print(e)

main1()
