import graphviz as gv
import networkx as nx

def show_network(network):
    graph = gv.Graph(format='svg')

    for node in network.nodes_iter():
        graph.node(str(node))

    for (f, to) in network.edges_iter():
        graph.edge(str(f), str(to))

    graph.render('img/graph', view=True)

g = nx.path_graph(10)
show_network(g)
