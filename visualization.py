import graphviz as gv
import networkx as nx
import github

def show_network(network):
    graph = gv.Digraph(format='gv')

    for node in network.nodes_iter():
        graph.node(str(node))

    for (f, to) in network.edges_iter():
        graph.edge(str(f), str(to))

    graph.render('img/graph', view=True)

def github_network(login, depth=1, edges=1000):
    graph = nx.DiGraph()
    edge_count = 0
    initial_user = github.User.fetch_single(login)
    searched = set()
    leaves = [initial_user]
    while len(leaves) != 0:
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
                        graph.add_node(contributor.login)
                        graph.add_edge(contributor.login, owner.login)
                        edge_count += 1
                        if edge_count > edges:
                            return graph
        leaves = new_leaves

    return graph

g = github_network('dsyme', depth=10, edges=1000)
for edge in g.edges_iter():
    print(edge)

show_network(g)
