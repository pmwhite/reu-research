import sqlite3

import github
import stack
import twitter

from itertools import groupby, islice
from misc import grouper
from network import github_network, stack_network, twitter_network, connections

def find_potential_common_users(conn):
    prev_rows = conn.execute('''
            SELECT su.*, tu.*, gu.* FROM StackUsers su
            JOIN TwitterUsers tu ON su.DisplayName = tu.ScreenName
            JOIN GithubUsers gu ON gu.Login = tu.ScreenName
            JOIN Dict WHERE su.DisplayName COLLATE NOCASE <= Dict.Value''')
    user_triples = ((stack.User(*row[0:6]), 
        twitter.User(*row[6:13]), 
        github.User(*row[13:20]))
        for row in prev_rows)
    grouped_triples = ((list(triple[0] for triple in triples), t_user, g_user) 
            for (t_user, g_user), triples in groupby(user_triples, lambda triple: triple[1:3]))
    for x in grouped_triples:
        yield x
    stack_rows = conn.execute('''
            SELECT su.* FROM StackUsers su
            JOIN Dict WHERE su.DisplayName COLLATE NOCASE > Dict.Value
            ORDER BY su.DisplayName COLLATE NOCASE''')
    stack_users = (stack.User(*row) for row in stack_rows)
    grouped_stack_users = ((k, list(vs)) 
            for k, vs in groupby(stack_users, lambda user: user.display_name))
    for _group in grouper(grouped_stack_users, 400):
        group = list(_group)
        cleaned_group = [(dn, users) for dn, users in group if ' ' not in dn]
        display_names = [dn for dn, _ in cleaned_group]
        stack_users_groups = {dn: users for dn, users in cleaned_group}
        twitter_users = twitter.user_fetch_screen_names(display_names, conn)
        github_users = github.user_fetch_logins(display_names, conn)
        for dn in display_names:
            su = stack_users_groups[dn]
            tu = twitter_users[dn]
            gu = github_users[dn]
            if su is not None and tu is not None and gu is not None:
                yield (su, tu, gu)
            conn.execute('UPDATE Dict SET Value = ?', (dn,))

def triple_rating(s, t, g):
    rating = 0
    if s.display_name == t.name and g.name == t.name:
        rating += 1
    if s.location == t.location and g.location == t.location and s.location is not None:
        rating += 1
    return rating

def best_triples(conn):
    potentials = find_potential_common_users(conn)
    for (s_users, t, g) in potentials:
        triples = [(s, t, g) for s in s_users]
        yield max(triples, key=lambda triple: triple_rating(*triple))

def good_triples(conn):
    return (triple for triple in best_triples(conn) if triple_rating(*triple) > 1)

def iter_at_least(iterator, n):
    return n - len(list(islice(iterator, n)))

def root_short(n, network, conn):
    users = set()
    for connection in connections(network, conn):
        users.add(connection)
        if len(users) >= n:
            break
    return n - len(users)

def unique_stack_matches(conn):
    for i, (s_users, t, g) in enumerate(find_potential_common_users(conn)):
        if len(s_users) == 1 and s_users[0].display_name == t.name and t.name == g.name:
            yield (s_users[0], t, g)

def active_matches(s_limit, t_limit, g_limit, conn):
    for s, t, g in unique_stack_matches(conn):
        s_short = root_short(s_limit, stack_network(s), conn)
        g_short = None
        t_short = None
        if s_short <= 0:
            g_short = root_short(g_limit, github_network(g), conn)
            if g_short <= 0:
                t_short = root_short(t_limit, twitter_network(t), conn)
                if t_short <= 0:
                    yield (s, t, g)
        print(s_short, t_short, g_short, g.login)

