from collections import namedtuple
from graph import Graph
import xml.etree.cElementTree as ET

GexfWritable = namedtuple('GexfWritable', 'schema serialize label')
CsvWritable = namedtuple('CsvWritable', 'to_row from_row cols')

def multi_gexf(schemas, type_legend):
    schema = {'node_type': 'string'}
    for t, (prefix, gexf)  in schemas:
        schema.update(misc.prefix_keys(gexf.schema, prefix))
    def multi_serialize(node):
        (prefix, gexf) = type_legend[type(node)]
        return misc.prefix_keys(gexf.serialize(node), prefix)
    def multi_labeler(node):
        (prefix, gexf) = type_legend[type(node)]
        return prefix + gexf.label(node)

def write_gexf(graph, gexf):
    root = ET.Element('gexf', xmlns='http://www.gexf.net/1.2draft', version='1.2')
    g = ET.Element('graph', mode='static', defaultedgetype='directed')
    nodes = ET.Element('nodes')
    attributes = ET.Element('attributes', {'class': 'node'})
    attr_key = {}
    for i, (a_name, a_type) in enumerate(gexf.schema.items()):
        attr_key[a_name] = i
        attributes.append(ET.Element('attribute', {'id': str(i), 'title': a_name, 'type': a_type}))
    attr_key = {attr: i for i, attr in enumerate(gexf.schema)}
    for node_id, node in graph.nodes.items():
        n = ET.Element('node', id=str(node_id), label=gexf.label(node))
        attvalues = ET.Element('attvalues')
        for k, v in gexf.serialize(node).items():
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

def write_csv(graph, csv, base_file, sep='|'):
    with open(base_file + '_nodes.csv', 'w') as f:
        f.write(sep.join(csv.cols) + '\n')
        f.writelines(h + sep + sep.join(csv.to_row(node)) + '\n' for h, node in graph.nodes.items())
    with open(base_file + '_edges.csv', 'w') as f:
        f.write('from' + sep + 'to\n')
        f.writelines(f + sep + t + '\n' for f, t in graph.edges)

def read_csv(graph, csv, base_file, sep='|'):
    nodes = {}
    edges = set()
    with open(base_file + '_nodes.csv', 'r') as f:
        cols = next(f)
        for line in f:
            row = line.split(sep)
            nodes[row[0]] = csv.from_row(row[1:])
    with open(base_file + '_edges.csv', 'r') as f:
        cols = next(f)
        for line in f:
            row = line.split(sep)
            edges.add(row[0], row[1])
    return Graph(nodes=nodes, edges=edges)
