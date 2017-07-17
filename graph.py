from collections import namedtuple
import xml.etree.cElementTree as ET
import misc
import itertools
import github
import twitter

Graph = namedtuple('Graph', 'nodes edges')

def empty_graph():
    return Graph(nodes={}, edges=set())

def add_edges_from(graph, edges_iter, hasher):
    for f, t in edges_iter:
        f_hash = hasher(f)
        t_hash = hasher(t)
        if f_hash not in graph.nodes:
            graph.nodes[f_hash] = f
        if t_hash not in graph.nodes:
            graph.nodes[t_hash] = t
        graph.edges.add((f_hash, t_hash))

def from_edges(edges_iter):
    graph = empty_graph()
    for f, t in edges_iter:
        f_hash = misc.hash(f)
        t_hash = misc.hash(t)
        if f_hash not in graph.nodes:
            graph.nodes[f_hash] = f
        if t_hash not in graph.nodes:
            graph.nodes[t_hash] = t
        graph.edges.add((f_hash, t_hash))
    return graph

def pull_n_nodes(n, edges_iter):
    graph = empty_graph()
    for f, t in edges_iter:
        f_hash = misc.hash(f)
        t_hash = misc.hash(t)
        if f_hash not in graph.nodes:
            graph.nodes[f_hash] = f
            misc.progress(n, len(graph.nodes))
        if t_hash not in graph.nodes:
            graph.nodes[t_hash] = t
            misc.progress(n, len(graph.nodes))
        graph.edges.add((f_hash, t_hash))
        if len(graph.nodes) >= n:
            break
    return graph

def union(g1, g2):
    return Graph(
            nodes={**g2.nodes, **g1.nodes},
            edges=(g1.edges | g2.edges))

def mash(g1, g2, seeds, masher):
    seed_data = {(misc.hash(n1), misc.hash(n2)): masher(n1, n2) for n1, n2 in seeds}
    h1_convert = {h1: misc.hash(seed) for (h1, h2), seed in seed_data.items()}
    h2_convert = {h2: misc.hash(seed) for (h1, h2), seed in seed_data.items()}
    all_nodes = {seed for (h1, h2), seed in seed_data.items()}.union(
            n1 for h1, n1 in g1.nodes.items() if h1 not in h1_convert).union(
                    n2 for h2, n2 in g2.nodes.items() if h2 not in h2_convert)
    all_edges = {(h1_convert.get(f, f), h1_convert.get(t, t)) for f, t in g1.edges}.union(
            (h2_convert.get(f, f), h2_convert.get(t, t)) for f, t in g2.edges)
    return Graph(
            nodes={misc.hash(node): node for node in all_nodes}, 
            edges=all_edges)

def to_gefx(graph, schema, serialize, labeler):
    root = ET.Element('gefx', xmlns='http://www.gefx.net/1.2draft', version='1.2')
    g = ET.Element('graph', mode='static', defaultedgetype='directed')
    nodes = ET.Element('nodes')
    attributes = ET.Element('attributes', {'class': 'node'})
    attr_key = {}
    for i, (a_name, a_type) in enumerate(schema.items()):
        attr_key[a_name] = i
        attributes.append(ET.Element('attribute', {'id': str(i), 'title': a_name, 'type': a_type}))
    attr_key = {attr: i for i, attr in enumerate(schema)}
    for node_id, node in graph.nodes.items():
        n = ET.Element('node', id=str(node_id), label=labeler(node))
        attvalues = ET.Element('attvalues')
        for k, v in serialize(node).items():
            if v is not None:
                attvalues.append(ET.Element('attvalue', {'for': str(attr_key[k]), 'value': str(v)}))
        n.append(attvalues)
        nodes.append(n)
    edges = ET.Element('edges')
    for index, (f, t) in enumerate(graph.edges):
        edges.append(ET.Element('edge', id=str(index), source=str(f), target=str(t)))
    g.append(attributes)
    g.append(nodes)
    g.append(edges)
    root.append(g)
    return ET.ElementTree(root)

def simple_gefx(graph, labeler):
    root = ET.Element('gefx', xmlns='http://www.gefx.net/1.2draft', version='1.2')
    g = ET.SubElement(root, 'graph', mode='static', defaultedgetype='directed')
    nodes = ET.SubElement(g, 'nodes')
    for node_id, node in graph.nodes.items():
        n = ET.SubElement(nodes, 'node', id=str(node_id), label=str(labeler(node)))
    edges = ET.SubElement(g, 'edges')
    for index, (f, t) in enumerate(graph.edges):
        ET.SubElement(edges, 'edge', id=str(index), source=str(f), target=str(t))
    return ET.ElementTree(root)

def write_twitter(graph, f):
    to_gefx(graph, 
            twitter.user_attribute_schema,
            twitter.serialize_user,
            lambda user: user.screen_name).write(f)

def write_github(graph, f):
    to_gefx(graph, 
            github.user_attribute_schema,
            github.serialize_user,
            lambda user: user.login).write(f)
