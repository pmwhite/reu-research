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

def fetch_many_db(query, identifiers, entity_creator, conn):
    def fetch_one(ident):
        db_response = conn.execute(query, (ident,)).fetchone()
        if db_response is not None:
            return entity_creator(*db_response)
    return {ident: fetch_one(ident) for ident in identifiers}

def cached_fetch(db_query, api_fetch_many, from_db, from_json, store, identifiers, conn):
    def fetch_one(ident):
        row = conn.execute(db_query, (ident,)).fetchone()
        if row is not None:
            return from_db(*row)
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
