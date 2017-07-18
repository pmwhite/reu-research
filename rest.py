import pickle
import shelve
import requests
import time
import sqlite3

shelf = shelve.open('data/shelf')

def find_str_db(s, conn):
    row = conn.execute('SELECT Response FROM HttpRequests WHERE Request = ?', [s]).fetchone()
    if row is not None:
        return pickle.loads(row[0])
    else:
        return None

def store_str_db(s, v, conn):
    conn.execute('REPLACE INTO HttpRequests VALUES(?,?)', [s, sqlite3.Binary(pickle.dumps(v))])
    conn.commit()


def cached_get(conn, path, params=None, **kwargs):
    h = str(b'get' + pickle.dumps(path) + pickle.dumps(params) + pickle.dumps(kwargs))
    obj = find_str_db(h, conn)
    if obj is not None:
        return (True, obj)
    else:
        response = None
        while response == None:
            try:
                response = requests.get(path, params=params, timeout=10, **kwargs)
            except Exception as e:
                print('didn\'t get response, trying again for you in 3 seconds')
                time.sleep(3)
        store_str_db(h, response, conn)
        return (False, response)

def cached_post(conn, url, data=None, json=None, **kwargs):
    h = str(b'post' + pickle.dumps(url) + pickle.dumps(data) + pickle.dumps(json) + pickle.dumps(kwargs))
    obj = find_str_db(h, conn)
    if obj is not None and 'errors' not in obj.json():
        return (True, obj)
    else:
        response = None
        while response == None:
            try:
                response = requests.post(url, data=data, json=json, timeout=10, **kwargs)
            except Exception as e:
                print('didn\'t get response, trying again for you in 3 seconds')
                time.sleep(3)
        store_str_db(h, response, conn)
        return (False, response)

def migrate_to_sqlite(conn):
    for i, request_str in enumerate(shelf.keys()):
        response = shelf[request_str]
        conn.execute('INSERT INTO HttpRequests VALUES(?,?)', (request_str, sqlite3.Binary(pickle.dumps(response))))
        if i % 1 == 0: print(i)
