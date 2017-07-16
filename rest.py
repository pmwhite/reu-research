import pickle
import shelve
import requests
import time

shelf = shelve.open('data/shelf')

def cached_get(path, params=None, **kwargs):
    h = str(b'get' + pickle.dumps(path) + pickle.dumps(params) + pickle.dumps(kwargs))
    if h in shelf:
        return (True, shelf[h])
    else:
        response = None
        while response == None:
            try:
                response = requests.get(path, params=params, timeout=10, **kwargs)
            except Exception as e:
                print('didn\'t get response, trying again for you in 3 seconds')
                time.sleep(3)
        shelf[h] = response
        return (False, response)

def cached_post(url, data=None, json=None, **kwargs):
    h = str(b'post' + pickle.dumps(url) + pickle.dumps(data) + pickle.dumps(json) + pickle.dumps(kwargs))
    if h in shelf and 'errors' not in shelf[h].json():
        return (True, shelf[h])
    response = None
    while response == None:
        try:
            response = requests.post(url, data=data, json=json, timeout=10, **kwargs)
        except Exception as e:
            print('didn\'t get response, trying again for you in 3 seconds')
            time.sleep(3)
    shelf[h] = response
    return (False, response)
