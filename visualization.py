import graphviz as gv
import networkx as nx
import github
import twitter
import sys

def save_network(network):
    graph = gv.Digraph(format='gv')

    for node in network.nodes_iter():
        graph.node(str(node))

    for (f, to) in network.edges_iter():
        graph.edge(str(f), str(to))

    graph.render(sys.argv[1])

def github_network(login, depth=1, edges=1000):
    graph = nx.DiGraph()
    edge_count = 0
    initial_user = github.User.fetch_single(login)
    searched = set()
    leaves = [initial_user]
    while leaves:
        new_leaves = []
        for owner in leaves:
            if owner.login in searched: 
                print('skipping owner', owner.login)
                continue
            else: 
                print('searching owner', owner.login)
                searched.add(owner.login)
                for repo in owner.repos():
                    if repo.is_fork:
                        continue
                    print('searching repo', repo.name)
                    for contributor in repo.contributors():
                        print('found contributor', contributor.login)
                        new_leaves.append(contributor)
                        graph.add_edge(contributor.login, owner.login)
                        edge_count += 1
                        if edge_count > edges:
                            return graph
        leaves = new_leaves
    return graph

def twitter_network(screen_name, depth=1, edges=1000):
    graph = nx.DiGraph()
    initial_user = twitter.User.fetch_single_screen_name(screen_name)
    edge_count = 0
    searched = set()
    leaves = [initial_user]
    while leaves:
        new_leaves = []
        for user in leaves:
            if user.user_id in searched:
                print('skipping user', user.screen_name)
                continue
            else:
                print('searching user', user.screen_name)
                for following in user.following():
                    print('found following', following.screen_name)
                    new_leaves.append(following)
                    graph.add_edge(following.screen_name, user.screen_name)
                    edge_count += 1
                    if edge_count > edges:
                        return graph
                for follower in user.followers():
                    print('found follower', follower.screen_name)
                    new_leaves.append(follower)
                    graph.add_edge(follower.screen_name, user.screen_name)
                    edge_count += 1
                    if edge_count > edges:
                        return graph


        leaves = new_leaves
    return graph

    
g = twitter_network('philmwhite', depth=10, edges=100)
for edge in g.edges_iter():
    print(edge)

save_network(g)
