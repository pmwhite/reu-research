"""This module contains functions for combining Twitter, GitHub, and
StackOverflow for analysis. It has some Twitter-GitHub-specific metrics for
de-anonymization, and it has functions for pulling common users between all
three sites from the APIs."""
import sqlite3
from itertools import groupby, islice
from rest import grouper
from network import degree
import deanon
import dataset
import github
import stack
import twitter

def check_username(username, conn):
"Checks whether there is a user with a certain username on all three sites."
    stack_rows = conn.execute(
            'SELECT * FROM StackUsers WHERE DisplayName = ?',
            [username]).fetchall()
    stack_users = [stack.User(*row) for row in stack_rows]
    twitter_user = twitter.user_fetch_screen_name(username, conn)
    github_user = github.user_fetch_login(username, conn)
    return (stack_users, twitter_user, github_user)

def username_matches(conn, after=None):
"Yields a triple of (StackOverflow users, Twitter user, and GitHub user). Every
user in the triple has the same username. Since stackoverflow may have multiple
users with the same username, we return a list of StackOverflow users in the
triple."
    if after is not None:
        stack_rows = conn.execute('''
                SELECT * FROM StackUsers
                WHERE DisplayName > ?
                ORDER BY DisplayName COLLATE NOCASE''', [after])
    else:
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

def unique_username_matches(conn, after=None):
"""Same as `username_matches` except only those with only one StackOverflow
username match. Because there is only one, the StackOverflow user is not inside
a list."""
    for s_users, t, g in username_matches(conn, after=after):
        if len(s_users) == 1 and s_users[0].display_name == t.name and t.name == g.name:
            yield (s_users[0], t, g)

def active_unique_username_matches(conn, s_limit, t_limit, g_limit, after=None):
"""Yields the triples of users in which all three users have a degree greater
than the specified amount for each of their respective networks."""
    for s, t, g in unique_username_matches(conn, after=after):
        if degree(s, stack.user_walk, conn) >= s_limit:
            if degree(g, github.user_walk, conn) >= g_limit:
                if degree(t, twitter.user_walk, conn) >= t_limit:
                    yield (s, t, g)

def tg_location_metric(attacker_data):
"""A metric for comparing Twitter and Github users based on their location
strings."""
    def metric(t, a):
        if t.location is not None and a.location is not None:
            return deanon.jaccard_string_index(t.location, a.location)
        else:
            return 0
    return metric

def tg_jaccard_location_metric(attacker_data):
"""A metric which is the sum of the jaccard metric and the location metric."""
    j_metric = deanon.jaccard_metric(attacker_data)
    l_metric = tg_location_metric(attacker_data)
    return lambda t, a: j_metric(t, a) + l_metric(t, a)

def tg_activity_metric(attacker_data):
"""A metric for comparing the activity histograms of Twitter and Github. The
similarity is essentially the cosine similarity of the time slot vectors."""
    conn = sqlite3.connect('data/data.db')
    t_histograms = {t: twitter.activity_histogram(t, 5, conn) for t in attacker_data.t_nodes}
    a_histograms = {a: github.activity_histogram(a, 5, conn) for a in attacker_data.a_nodes}
    def metric(t, a):
        return deanon.cosine_similarity(t_histograms[t], a_histograms[a])
    return metric

def tg_is_seed(t_user, g_user):
"Checks whether a Github and Twitter user match enough to be considered a seed."
    return (g_user.login == t_user.screen_name or
            (g_user.name is not None and 
            t_user.name is not None and 
            ' ' in g_user.name and 
            g_user.name == t_user.name))

def tg_scenario(conn):
"A scenario for getting a Twitter-Github dataset."
    return dataset.Scenario(
        t_walk=twitter.user_walk(conn),
        a_walk=github.user_walk(conn),
        seed_pred=tg_is_seed)

"A serializer for Twitter and Github"
tg_gexf = dataset.mashed_gexf(twitter.user_gexf, github.user_gexf)
