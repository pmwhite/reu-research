import itertools
import time
from datetime import datetime

def grouper(iterable, n):
    args = [iter(iterable)] * n
    for group in itertools.zip_longest(*args, fillvalue=None):
        yield list(filter(lambda x: x is not None, group))

def clean_str(s):
    if s == '': return None
    else: return s

def rated_request(make_request, extract_rate_info):
    response = make_request()
    (reset_time, requests_left) = extract_rate_info(response)
    time_before_reset = reset_time - datetime.utcnow().timestamp()
    if requests_left <= 1: delay_time = time_before_reset + 5
    else: delay_time = time_before_reset / requests_left
    print('time left:', time_before_reset, ', requests left:', requests_left, ', delaying:', delay_time)
    time.sleep(max(0.5,delay_time))
    return response

def paginate_api(make_request, extract_cursor, extract_items):
    response = make_request(None)
    next_cursor = extract_cursor(response)
    while response.status_code == 200:
        for item in extract_items(response):
            yield item
        if not next_cursor:
            break
        response = make_request(next_cursor)
        next_cursor = extract_cursor(response)

class CachedSearch:
    def __init__(self, db_fetch, api_fetch, store, search_type):
        self.db_fetch = db_fetch
        self.api_fetch = api_fetch
        self.search_type = search_type
        self.store = store

    def __call__(self, entity, conn):
        if self.is_searched(entity, conn):
            for item in self.db_fetch(entity, conn):
                yield item
        else:
            for item in self.api_fetch(entity):
                self.store(entity, item, conn)
                yield item
            conn.execute(
                    'INSERT INTO ApiSearches VALUES(?,?)',
                    (entity.id, self.search_type))
            conn.commit()

    def is_searched(self, entity, conn):
        row = conn.execute('''
            SELECT * FROM ApiSearches 
            WHERE EntityId = ? 
            AND SearchType = ?''',
            (entity.id, self.search_type)).fetchone()
        return row is not None
