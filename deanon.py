import sqlite3
import common
import stack 
import github
import twitter
from itertools import islice, product
from network import stack_walk, twitter_walk, github_walk, walk_edges
import graph
from collections import deque

def levenshtein(s1, s2):
    w = len(s1) + 1
    h = len(s2) + 1
    matrix = [[0 for y in range(h)] for x in range(w)]
    for i in range(1, w): matrix[i][0] = i
    for i in range(1, h): matrix[0][i] = i
    for x in range(1, w):
        for y in range(1, h):
            subCost = 1
            if s1[x-1] == s2[y-1]:
                subCost = 0
            matrix[x][y] = min(
                    matrix[x-1][y] + 1,
                    matrix[x][y-1] + 1,
                    matrix[x-1][y-1] + subCost)
    return matrix[w-1][h-1]

def lcs(s1, s2):
    w = len(s1)
    h = len(s2)
    matrix = [[0 for y in range(h)] for x in range(w)]
    z = 0
    for x in range(w):
        for y in range(h):
            if s1[x] == s2[y]:
                if x == 0 or y == 0:
                    matrix[x][y] = 1
                else:
                    matrix[x][y] = matrix[x-1][y-1] + 1
                z = max(z, matrix[x][y])
            else:
                matrix[x][y] = 0
    return z

def diag_product(it1, it2):
    acc1 = []
    acc2 = []
    for index, (x1, x2) in enumerate(zip(it1, it2)):
        acc1.append(x1)
        acc2.append(x2)
        for i in range(index + 1):
            yield (acc1[i], acc2[index - i])
        index += 1

def tg_pred(t_user, g_user):
    if g_user.login == t_user.screen_name:
        return True
    elif g_user.name is not None and t_user.name is not None and ' ' in g_user.name and g_user.name == t_user.name:
        return True
    else:
        return False

def graph_seeds(g1, g2, pred):
    pairs = product(g1.nodes.values(), g2.nodes.values())
    return {pair for pair in pairs if pred(*pair)}

def new_seed_tg(t_user, g_user, max_seeds, conn):
    t_graph = graph.empty_graph()
    g_graph = graph.empty_graph()
    seeds = {(t_user, g_user): (
                        walk_edges(t_user, twitter_walk, conn),
                        walk_edges(g_user, github_walk, conn))}
    while len(seeds) < max_seeds:
        new_seeds = set()
        for (t_seed, g_seed), (t_edges, g_edges) in seeds.items():
            print('searching', t_seed.screen_name)
            t_exploration = graph.from_edges(islice(t_edges, 100), hasher=lambda user: user.id)
            g_exploration = graph.from_edges(islice(g_edges, 300), hasher=lambda user: user.id)
            print(len(t_exploration.nodes), len(g_exploration.nodes))
            new_seeds.update(graph_seeds(t_graph, g_exploration, tg_pred))
            new_seeds.update(graph_seeds(t_exploration, g_graph, tg_pred))
            new_seeds.update(graph_seeds(t_exploration, g_exploration, tg_pred))
            print(new_seeds)
            t_graph = graph.union(t_graph, t_exploration)
            g_graph = graph.union(g_graph, g_exploration)

        for pair in new_seeds:
            if pair not in seeds:
                seeds[pair] = (
                        walk_edges(pair[0], twitter_walk, conn),
                        walk_edges(pair[1], github_walk, conn))
        print(len(t_graph.nodes), len(g_graph.nodes))
        print(len(seeds), seeds)
    return (t_graph, g_graph)

def queue_seed_tg(t_user, g_user, max_seeds, conn):
    search_queue = deque()
    t_edges = walk_edges(t_user, twitter_walk, conn)
    g_edges = walk_edges(g_user, github_walk, conn)
    t_graph = graph.empty_graph()
    g_graph = graph.empty_graph()
    last_seeds = set()
    last_t_size
    while len(last_seeds) < max_seeds:
        graph.add_edges_from(t_graph, islice(t_edges, 100), lambda user: user.id)
        graph.add_edges_from(g_graph, islice(g_edges, 300), lambda user: user.id)
        t_nodes = list(t_graph.nodes.values())
        g_nodes = list(g_graph.nodes.values())
        print(len(t_nodes))
        print(len(g_nodes))
        pairs = product(t_nodes, g_nodes)
        seeds = {pair for pair in pairs if tg_pred(*pair)}
        print(seeds)
        if len(seeds) > len(last_seeds):
            for seed in seeds - last_seeds:
                search_queue.append(seed)
            print(seeds)
            print(len(seeds))
            if len(search_queue) != 0:
                (t_center, g_center) = search_queue.popleft()
                print('switching...', t_center.screen_name, g_center.login)
                t_edges = walk_edges(t_center, twitter_walk, conn)
                g_edges = walk_edges(g_center, github_walk, conn)
                last_seeds = seeds
            else:
                break
    return (t_graph, g_graph)

def seed_tg(t_user, g_user, max_seeds, conn):
    t_edges = walk_edges(t_user, twitter_walk, conn)
    g_edges = walk_edges(g_user, github_walk, conn)
    t_graph = graph.empty_graph()
    g_graph = graph.empty_graph()
    last_seeds = set()
    while len(last_seeds) < max_seeds:
        graph.add_edges_from(t_graph, islice(t_edges, 100), lambda user: user.id)
        graph.add_edges_from(g_graph, islice(g_edges, 300), lambda user: user.id)
        t_nodes = list(t_graph.nodes.values())
        g_nodes = list(g_graph.nodes.values())
        print(len(t_nodes))
        print(len(g_nodes))
        pairs = product(t_nodes, g_nodes)
        seeds = {pair for pair in pairs if tg_pred(*pair)}
        print(seeds)
        if len(seeds) > len(last_seeds):
            (t_center, g_center) = next(iter(seeds - last_seeds))
            print('switching...', t_center.screen_name, g_center.login)
            print(seeds)
            print(len(seeds))
            t_edges = walk_edges(t_center, twitter_walk, conn)
            g_edges = walk_edges(g_center, github_walk, conn)
            last_seeds = seeds
    return (t_graph, g_graph)

def tg_metric(t_user, g_user):
    total = lcs(t_user.screen_name, g_user.login)
    if g_user.name is not None and t_user.name is not None and g_user.name == t_user.name:
        total += 100
    return total

def find_seeds(triple, conn):
    (s_user, t_user, g_user) = triple
    s_c = nodes_iter(stack_network(s_user), conn)
    t_c = nodes_iter(twitter_network(t_user), conn)
    g_c = nodes_iter(github_network(g_user), conn)
    pairs = {pair for pair in islice(diag_product(t_c, g_c), 10000)}
    scored = [(tg_metric(*pair), pair) for pair in pairs]
    best = islice(sorted(scored, key=lambda x: x[0], reverse=True), 200)
    for pair in best:
        print(pair)
