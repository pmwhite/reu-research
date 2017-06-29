import itertools
def grouper(iterable, n):
    args = [iter(iterable)] * n
    for group in itertools.zip_longest(*args, fillvalue=None):
        yield filter(lambda x: x != None, group)

def clean_str(s):
    if s == '': return None
    else: return s


