import itertools
import time
import hashlib
import pickle
from datetime import datetime

def grouper(iterable, n):
    args = [iter(iterable)] * n
    for group in itertools.zip_longest(*args, fillvalue=None):
        yield list(filter(lambda x: x is not None, group))

def clean_str_key(data, key):
    s = data.get(key, None)
    if s == '': return None
    else: return s

def rated_request(make_request, extract_rate_info):
    (cached, response) = make_request()
    if not cached:
        (reset_time, requests_left) = extract_rate_info(response)
        time_before_reset = reset_time - datetime.utcnow().timestamp()
        if requests_left <= 1: delay_time = time_before_reset + 5
        else: delay_time = time_before_reset / requests_left
        print('time left:', time_before_reset, ', requests left:', requests_left, ', delaying:', delay_time)
        time.sleep(max(0.1,delay_time))
    return response

def paginate_api(make_request, extract_cursor, extract_items):
    response = make_request(None)
    while response.status_code == 200:
        next_cursor = extract_cursor(response)
        for item in extract_items(response):
            yield item
        if next_cursor is None:
            break
        response = make_request(next_cursor)

def progress(goal, current):
    c = int(current / goal * 100)
    print('|' + ('=' * c).ljust(100) + '|')

def hash(obj):
    return hashlib.sha256(pickle.dumps(obj)).digest()

def prefix_keys(d, prefix):
    return {prefix + key: value for key, value in d.items()}
