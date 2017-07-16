import sqlite3
import github
import stack
import twitter
from itertools import groupby, islice
from misc import grouper
from network import stack_walk, twitter_walk, github_walk, degree

def find_potential_common_users(conn):
    stack_rows = conn.execute('''
            SELECT * FROM StackUsers
            ORDER BY DisplayName COLLATE NOCASE''')
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

def unique_stack_matches(conn):
    for i, (s_users, t, g) in enumerate(find_potential_common_users(conn)):
        if len(s_users) == 1 and s_users[0].display_name == t.name and t.name == g.name:
            yield (s_users[0], t, g)

def active_matches(s_limit, t_limit, g_limit, conn):
    for s, t, g in unique_stack_matches(conn):
        s_deg = degree(s, stack_walk, conn)
        g_deg = None
        t_deg = None
        if s_deg >= s_limit:
            g_deg = degree(g, github_walk, conn)
            if g_deg >= g_limit:
                t_deg = degree(t, twitter_walk, conn)
                if t_deg >= t_limit:
                    yield (s, t, g)
        print(s_deg, t_deg, g_deg, g.login)
