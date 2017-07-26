from itertools import groupby, islice
from rest import grouper
from network import degree
import deanon
import dataset
import github
import stack
import twitter

def check_username(username, conn):
    stack_rows = conn.execute(
            'SELECT * FROM StackUsers WHERE DisplayName = ?',
            [username]).fetchall()
    stack_users = [stack.User(*row) for row in stack_rows]
    twitter_user = twitter.user_fetch_screen_name(username, conn)
    github_user = github.user_fetch_login(username, conn)
    return (stack_users, twitter_user, github_user)

def username_matches(conn, after=None):
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
    for s_users, t, g in username_matches(conn, after=after):
        if len(s_users) == 1 and s_users[0].display_name == t.name and t.name == g.name:
            yield (s_users[0], t, g)

def active_unique_username_matches(conn, s_limit, t_limit, g_limit, after=None):
    for s, t, g in unique_username_matches(conn, after=after):
        if degree(s, stack.user_walk, conn) >= s_limit:
            if degree(g, github.user_walk, conn) >= g_limit:
                if degree(t, twitter.user_walk, conn) >= t_limit:
                    yield (s, t, g)

def tg_is_seed(t_user, g_user):
    return (g_user.login == t_user.screen_name or
            (g_user.name is not None and 
            t_user.name is not None and 
            ' ' in g_user.name and 
            g_user.name == t_user.name))

def tg_scenario(conn):
    return dataset.Scenario(
        t_walk=twitter.user_walk(conn),
        a_walk=github.user_walk(conn),
        seed_pred=tg_is_seed)

tg_gexf = dataset.mashed_gexf(twitter.user_gexf, github.user_gexf)
