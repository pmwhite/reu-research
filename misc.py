import hashlib
import pickle
from collections import deque

def progress(goal, current):
    c = int(current / goal * 100)
    print('|' + ('=' * c).ljust(100) + '|', str(current) + '/' + str(goal))

def progress_list(l):
    goal = len(l)
    for i, item in enumerate(l):
        progress(goal, i)
        yield item

def hash(obj):
    return hashlib.sha256(pickle.dumps(obj)).digest()

def prefix_keys(d, prefix):
    return {prefix + key: value for key, value in d.items()}

def select_keys(d, keys):
    return {d[key] for key in keys}

def breadth_first_walk_from(roots, expand):
    found = set(roots)
    search_queue = deque(found)
    yield from search_queue
    while len(search_queue) != 0:
        x = search_queue.popleft()
        expanded = expand(x)
        if expanded == None:
            return
        for item in expanded:
            if item not in found:
                found.add(item)
                yield item
                search_queue.append(item)

def breadth_first_walk(root, expand):
    return breadth_first_walk_from({root}, expand)

def hop_iter_from(roots, expand):
    found = set(roots)
    leaves = set(found)
    while len(leaves) != 0:
        yield leaves
        new_leaves = set()
        for leaf in leaves:
            new_leaves.update(item for item in expand(leaf) if item not in found)
        leaves = new_leaves - found
        found = found | new_leaves

def hop_iter(root, expand):
    return hop_iter_from({root}, expand)
