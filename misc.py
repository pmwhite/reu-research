import itertools
import time
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
    response = make_request()
    (reset_time, requests_left) = extract_rate_info(response)
    time_before_reset = reset_time - datetime.utcnow().timestamp()
    if requests_left <= 1: delay_time = time_before_reset + 5
    else: delay_time = time_before_reset / requests_left
    print('time left:', time_before_reset, ', requests left:', requests_left, ', delaying:', delay_time)
    time.sleep(max(0.1,delay_time))
    return response

def paginate_api(make_request, extract_cursor, extract_items):
    response = make_request(None)
    next_cursor = extract_cursor(response)
    while response.status_code == 200:
        for item in extract_items(response):
            yield item
        if next_cursor is None:
            break
        response = make_request(next_cursor)
        next_cursor = extract_cursor(response)

def fetch_many_db(query, identifiers, entity_creator, conn):
    def fetch_one(ident):
        db_response = conn.execute(query, (ident,)).fetchone()
        if db_response is not None:
            return entity_creator(*db_response)
    return {ident: fetch_one(ident) for ident in identifiers}

def cached_fetch(db_query, api_fetch_many, from_db, from_json, store, identifiers, conn):
    def fetch_one(ident):
        db_response = conn.execute(db_query, (ident,)).fetchone()
        if db_response is not None:
            return from_db(*db_response)
    result = {ident: fetch_one(ident) for ident in identifiers}
    api = api_fetch_many([ident for ident, entity in result.items() if entity is None])
    for ident, entity in api.items():
        if entity is not None:
            store(entity, conn)
            result[ident] = entity
    return result

def cached_search(entity, db_search, global_search, store, search_type, conn):
    row = conn.execute('''
            SELECT * FROM ApiSearches 
            WHERE EntityId = ? 
            AND SearchType = ?''',
            (entity.id, search_type)).fetchone()
    if row is not None:
        for item in db_search(entity, conn):
            yield item
    else:
        for item in global_search(entity, conn):
            store(entity, item, conn)
            yield item
        conn.execute(
                'INSERT INTO ApiSearches VALUES(?,?)',
                (entity.id, search_type))
        conn.commit()

def levenshtein(s1, s2):
    w = len(s1) + 1
    h = len(s2) + 1
    matrix = [[0 for y in range(h)] for x in range(w)]
    for i in range(1, w): matrix[i][0] = i
    for i in range(1, h): matrix[0][i] = i
    for x in range(1, w):
        for y in range(1, h):
            subCost = 1
            if s1[x-1] == s2[y-1]:
                subCost = 0
            matrix[x][y] = min(
                    matrix[x-1][y] + 1,
                    matrix[x][y-1] + 1,
                    matrix[x-1][y-1] + subCost)
    return matrix[w-1][h-1]

def lcs(s1, s2):
    w = len(s1)
    h = len(s2)
    matrix = [[0 for y in range(h)] for x in range(w)]
    z = 0
    for x in range(w):
        for y in range(h):
            if s1[x] == s2[y]:
                if x == 0 or y == 0:
                    matrix[x][y] = 1
                else:
                    matrix[x][y] = matrix[x-1][y-1] + 1
                z = max(z, matrix[x][y])
            else:
                matrix[x][y] = 0
    return z





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
