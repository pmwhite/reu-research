from collections import namedtuple

Table = namedtuple('Table', 'matrix xs ys')

def table_apply(xs, ys, f):
    return Table(
            matrix=[[f(x, y) for x in xs] for y in ys], 
            xs={item: i for i, item in enumerate(xs)}, 
            ys={item: i for i, item in enumerate(ys)})

def index(table, x, y):
    (matrix, xs, ys) = table
    return matrix[ys[y]][xs[x]]

def to_str(table):
    return '\n'.join(' '.join('%.3d' % (cell * 100) for cell in row) for row in table.matrix)

def cells(table):
    (matrix, xs, ys) = table
    for y, yi in table.ys.items():
        row = table.matrix[yi]
        for x, xi in table.xs.items():
            yield (x, y, row[xi])
