import graphviz as gv
import networkx as nx
import twitter
import stack
import github
import sqlite3
from collections import namedtuple
from itertools import islice, chain

Network = namedtuple('Network', 'init child_gen parent_gen transform_leaves serialize')
Walk = namedtuple('Walk', 'out_gen in_gen select_leaves')

def walk_edges(init, walk, conn):
    nodes = {init}
    leaves = {init}
    while len(leaves) != 0:
        new_leaves = set()
        for leaf in walk.select_leaves(leaves):
            for out_node in walk.out_gen(leaf, conn): 
                new_leaves.add(out_node)
                yield (leaf, out_node)
            for in_node in walk.in_gen(leaf, conn):
                new_leaves.add(in_node)
                yield (in_node, leaf)
        leaves = new_leaves - nodes
        nodes = nodes.union(leaves)

def github_out_gen(user, conn):
    for repo in github.user_contributed_repos(user, conn):
        yield github.user_fetch_login(repo.owner_login, conn)

def github_in_gen(user, conn):
    for repo in github.user_repos(user, conn):
        if not repo.is_fork:
            for contributor in github.repo_contributors(repo, conn):
                yield contributor

def github_select_leaves(leaves): 
    for leaf in leaves:
        if leaf.login == 'Try-Git':
            continue
        else: 
            yield leaf

github_walk = Walk(
        out_gen=github_out_gen,
        in_gen=github_in_gen,
        select_leaves=github_select_leaves)

def twitter_out_gen(user, conn):
    for friend in twitter.user_friends(user, conn):
        yield friend

def twitter_in_gen(user, conn): return []

def twitter_select_leaves(leaves):
    sorted_leaves =  list(sorted(leaves, 
        key=lambda f: max(f.follower_count, f.following_count)))
    midpoint = int(len(sorted_leaves) / 2)
    s = max(midpoint - 25, 0)
    e = max(midpoint + 25, len(sorted_leaves))
    return sorted_leaves[s:e]

twitter_walk = Walk(
        out_gen=twitter_out_gen,
        in_gen=twitter_in_gen,
        select_leaves=twitter_select_leaves)

def stack_out_gen(user, conn): return stack.user_questioners(user, conn)

def stack_in_gen(user, conn): return stack.user_answerers(user, conn)

def stack_select_leaves(leaves): return leaves

stack_walk = Walk(
        out_gen=stack_out_gen,
        in_gen=stack_in_gen,
        select_leaves=stack_select_leaves)

def connections(x, walk, conn):
    return chain(walk.out_gen(x, conn), walk.in_gen(x, conn))

def degree(x, walk, conn):
    return len(list(connections(x, walk, conn)))
