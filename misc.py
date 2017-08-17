"""A module containing some general-purpose utility functions. These functions
aren't specific to any part of the project, although they may be used by some
more than others."""
import hashlib
import pickle
from collections import deque
from datetime import datetime, time

def progress(goal, current):
"""Display a progress bar of the percentage of the specified goal that the
current progress is."""
    c = int(current / goal * 100)
    print('|' + ('=' * c).ljust(100) + '|', str(current) + '/' + str(goal))

def progress_list(l):
"""Create an iterator from a list that displays a progress bar for each item
enumerated."""
    goal = len(l)
    for i, item in enumerate(l):
        progress(goal, i)
        yield item

def hash(obj):
"Return a cryptographic hash of the pickled representation of an object."
    return hashlib.sha256(pickle.dumps(obj)).digest()

def prefix_keys(d, prefix):
"Prefix all keys in a dictionary with a certain string."
    return {prefix + key: value for key, value in d.items()}

def select_keys(d, keys):
"Create a dict with a subset of keys from another dict."
    return {d[key] for key in keys}

def breadth_first_walk_from(roots, expand):
"""Walks outward from a set of central nodes, yielding each node as it is
encountered.  The given `expand` function takes a node and yields it's
neighboring node. The central nodes are the first to be yielded."""
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
"Same as `breadth_first_walk_from` except with a single node at the center."
    return breadth_first_walk_from({root}, expand)

def hop_iter_from(roots, expand):
"""Hops outward from a set of central nodes. This is different from the
breadth-first walk because it yield groups of nodes rather than a continuous
stream. The given expander gets the neighboring nodes of a specific node."""
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
"Same as `hop_iter_from` but with a single central node."
    return hop_iter_from(set(root), expand)

def day_seconds(dt):
"Finds how many seconds a into the day a certain datetime is."
    day_start = datetime.combine(dt.date(), time(0))
    return (dt - day_start).seconds

def activity_histogram(dts, num_blocks, conn):
"""Given some datetimes and n partitions, partitions the day into a `n` blocks
and finds the frequency of the datetimes landing in each partition."""
    block_counts = {i: 0 for i in range(num_blocks)}
    seconds_in_a_day = 24 * 60 * 60
    block_length = seconds_in_a_day / num_blocks
    for dt in dts:
        block_counts[int(day_seconds(dt) / block_length - 0.5)] += 1
    return [block_counts[i] for i in range(num_blocks)]
