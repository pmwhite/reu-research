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
        write_gexf(dset.target, twitter.user_gexf).write('funfun/abidibo_main1')

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

def argparser():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command_name')

    list_parser = subparsers.add_parser('list')
    list_parser.add_argument('-a', '--after', type=str, default=None)
    list_parser.add_argument('-n', '--amount', type=int, default=20)
    list_parsers = list_parser.add_subparsers(dest='list_type')
    list_parsers.add_parser('matches')
    list_parsers.add_parser('unique')
    list_active_parser = list_parsers.add_parser('active')
    list_active_parser.add_argument('--s_limit', type=int, default=20)
    list_active_parser.add_argument('--t_limit', type=int, default=20)
    list_active_parser.add_argument('--g_limit', type=int, default=8)

    check_user_parser = subparsers.add_parser('check_user')
    check_user_parser.add_argument('username')

    graph_parser = subparsers.add_parser('graph')
    graph_parser.add_argument('username')
    graph_parser.add_argument('out_dir')
    graph_parser.add_argument('--github', nargs='?', const=True, default=False)
    graph_parser.add_argument('--twitter', nargs='?', const=True, default=False)
    graph_parser.add_argument('--stack', nargs='?', const=True, default=False)
    graph_parser.add_argument('-n', '--nodes', type=int, default=6000)

    deanon_parser = subparsers.add_parser('pack_attack')
    deanon_parser.add_argument('username')
    deanon_parser.add_argument('out_dir')
    deanon_parser.add_argument('--github', nargs='?', const=True, default=False)
    deanon_parser.add_argument('--stack', nargs='?', const=True, default=False)
    deanon_parser.add_argument('-n', '--nodes', type=int, default=10000)
    deanon_parser.add_argument('-s', '--seeds', type=int, default=20)
    deanon_parser.add_argument('-b', '--batch', type=int, default=500)

    parsed = parser.parse_args()
    print(parsed)
    conn = sqlite3.connect('data/data.db')
    if parsed.command_name == 'list':
        if parsed.list_type == 'matches':
            list_matches(conn, after=parsed.after, amount=parsed.amount)
        elif parsed.list_type == 'unique':
            list_unique(conn, after=parsed.after, amount=parsed.amount)
        elif parsed.list_type == 'active':
            list_active(conn,
                    after=parsed.after,
                    s_limit=parsed.s_limit,
                    t_limit=parsed.t_limit,
                    g_limit=parsed.g_limit,
                    amount=parsed.amount)
    elif parsed.command_name == 'check_user':
        check_user(conn, parsed.username)
    elif parsed.command_name == 'graph':
        pull_username_graph(
                conn, parsed.username, 
                parsed.stack, parsed.twitter, parsed.github, 
                parsed.nodes, parsed.out_dir)
    elif parsed.command_name == 'pack_attack':
        deanon_user(conn, 
                username=parsed.username, 
                seeds=parsed.seeds, 
                nodes=parsed.nodes, 
                batch=parsed.batch, 
                out_dir=parsed.out_dir)

main1()
