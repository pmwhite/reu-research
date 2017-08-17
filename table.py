"A simple module for data tables."
from collections import namedtuple

Table = namedtuple('Table', 'matrix xs ys')

def table_apply(xs, ys, f):
"""Create a 'multiplication' table from an array of values and a function to
apply to them."""
    return Table(
            matrix=[[f(x, y) for x in xs] for y in ys], 
            xs={item: i for i, item in enumerate(xs)}, 
            ys={item: i for i, item in enumerate(ys)})

def index(table, x, y):
"Get an item from the table using the given parameters."
    (matrix, xs, ys) = table
    return matrix[ys[y]][xs[x]]

def to_str(table):
"Pretty-print a table."
    return '\n'.join(' '.join('%.3d' % (cell * 100) for cell in row) for row in table.matrix)

def cells(table):
"""Iterate through each cell in a table. Each cell is a triple of the
parameters used to generate the cell, along with the actual value inside the
cell."""
    (matrix, xs, ys) = table
    for y, yi in table.ys.items():
        row = table.matrix[yi]
        for x, xi in table.xs.items():
            yield (x, y, row[xi])
