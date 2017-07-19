from collections import namedtuple
import xml.etree.cElementTree as ET

NodeVisualizer = namedtuple('NodeVisualizer', 'schema serialize label')

def multi_visualization(schemas, type_legend):
    schema = {'node_type': 'string'}
    for t, (prefix, node_vis)  in schemas:
        schema.update(misc.prefix_keys(node_vis.schema, prefix))
    def multi_serialize(node):
        (prefix, nod_vis) = type_legend[type(node)]
        return misc.prefix_keys(node_vis.serialize(node), prefix)
    def multi_labeler(node):
        (prefix, node_vis) = type_legend[type(node)]
        return prefix + node_vis.label(node)

def graph_to_gefx(graph, node_vis):
    root = ET.Element('gefx', xmlns='http://www.gefx.net/1.2draft', version='1.2')
    g = ET.Element('graph', mode='static', defaultedgetype='directed')
    nodes = ET.Element('nodes')
    attributes = ET.Element('attributes', {'class': 'node'})
    attr_key = {}
    for i, (a_name, a_type) in enumerate(node_vis.schema.items()):
        attr_key[a_name] = i
        attributes.append(ET.Element('attribute', {'id': str(i), 'title': a_name, 'type': a_type}))
    attr_key = {attr: i for i, attr in enumerate(node_vis.schema)}
    for node_id, node in graph.nodes.items():
        n = ET.Element('node', id=str(node_id), label=node_vis.label(node))
        attvalues = ET.Element('attvalues')
        for k, v in node_vis.serialize(node).items():
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
