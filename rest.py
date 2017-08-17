"""Utility methods for interacting with rest apis efficiently. 'Efficiency' is
possible through infinitely aggressive caching."""
import itertools
import requests
import sqlite3
import time
import pickle
from datetime import datetime

def grouper(iterable, n):
"Utility to group an iterable into lists of a specified size."
    args = [iter(iterable)] * n
    for group in itertools.zip_longest(*args, fillvalue=None):
        yield list(filter(lambda x: x is not None, group))

def clean_str_key(data, key):
"""Utility to get a key from a dict, but return an empty string if the key does
not exist."""
    s = data.get(key, None)
    if s == '': return None
    else: return s

request_timing_info = {}

def rated_request(make_request, extract_rate_info, rate_family):
"""Higher-order function which handles rate limiting. Two functions are
supplied: one which actually makes the request, which is then handed to a
function which extracts the rate limit info from the request. This info is used
to delay for enough time to satisfy the rate limit. A `rate_family` parameter is used because sometimes two requests are not on the same rate limit. Requests using the same rate limit should have the same `rate_family`."""
    (cached, response) = make_request()
    if not cached:
        (reset_time, requests_left) = extract_rate_info(response)
        time_before_reset = reset_time - datetime.utcnow().timestamp()
        if requests_left <= 1: delay_time = time_before_reset + 5
        else: delay_time = time_before_reset / requests_left - 0.5
        print('time left:', time_before_reset, ', requests left:', requests_left, ', delaying:', delay_time)
        request_timing_info[rate_family] = datetime.utcnow().timestamp() + max(0.05, delay_time)
    return response

def find_str_db(s, conn):
"Very specific helper function that grabs a pickled object from a database."
    row = conn.execute('SELECT Response FROM HttpRequests WHERE Request = ?', [s]).fetchone()
    if row is not None:
        return pickle.loads(row[0])
    else:
        return None

def store_str_db(s, v, conn):
"""Stores an object into a database by pickling (I like pickling because I like
pickles) it."""
    conn.execute('REPLACE INTO HttpRequests VALUES(?,?)', [s, sqlite3.Binary(pickle.dumps(v))])
    conn.commit()

def cached_get(conn, rate_family, path, params=None, **kwargs):
"""An important function. Makes a request from an API. The request parameters
are stringified and concatenated; if the string is in the database, then the
cached result is returned."""
    h = str(b'get' + pickle.dumps(path) + pickle.dumps(params) + pickle.dumps(kwargs))
    obj = find_str_db(h, conn)
    if obj is not None:
        return (True, obj)
    else:
        curr_time = datetime.utcnow().timestamp()
        delay_time = request_timing_info.get(rate_family, 0) - curr_time
        print('delaying:', delay_time)
        time.sleep(max(0, delay_time))
        response = None
        while response == None:
            try:
                response = requests.get(path, params=params, timeout=10, **kwargs)
            except Exception as e:
                print('didn\'t get response, trying again for you in 3 seconds')
                time.sleep(3)
        store_str_db(h, response, conn)
        return (False, response)

def cached_post(conn, rate_family, url, data=None, json=None, **kwargs):
"Similar to `cached_get` but with `POST` requests."
    h = str(b'post' + pickle.dumps(url) + pickle.dumps(data) + pickle.dumps(json) + pickle.dumps(kwargs))
    obj = find_str_db(h, conn)
    if obj is not None and 'errors' not in obj.json():
        return (True, obj)
    else:
        curr_time = datetime.utcnow().timestamp()
        delay_time = request_timing_info.get(rate_family, 0) - curr_time
        print('delaying:', delay_time)
        time.sleep(max(0, delay_time))
        response = None
        while response == None:
            try:
                response = requests.post(url, data=data, json=json, timeout=10, **kwargs)
            except Exception as e:
                print('didn\'t get response, trying again for you in 3 seconds')
                time.sleep(3)
        store_str_db(h, response, conn)
        return (False, response)

def paginate_api(make_request, extract_cursor, extract_items):
"""A higher-order function for handling API pagination. One function makes the
requests. Another function somehow extracts page info or a cursor. A final
function extracts the actually interesting data inside the request."""
    response = make_request(None)
    while response.status_code == 200:
        next_cursor = extract_cursor(response)
        for item in extract_items(response):
            yield item
        if next_cursor is None:
            break
        response = make_request(next_cursor)
