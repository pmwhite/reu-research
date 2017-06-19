import requests
import keys
import itertools
import time
import sqlite3

token_reponse = requests.post(
        'https://api.twitter.com/oauth2/token?grant_type=client_credentials',
        auth=(keys.TWITTER_API, keys.TWITTER_SECRET)).json()

access_token = token_reponse['access_token']
auth_headers = {'Authorization': 'Bearer ' + access_token}

def rated_request(url, params={}):
    rate_limit_state = requests.get(
            'https://api.twitter.com/1.1/application/rate_limit_status.json?resources=users',
            headers=auth_headers).json()['resources']['users']['/users/lookup']

    time_before_reset = int(rate_limit_state['reset']) - time.time()
    requests_left = int(rate_limit_state['remaining'])
    
    if requests_left <= 1: delay_time = time_before_reset + 5
    else: delay_time = time_before_reset / requests_left

    time.sleep(max(0.5,delay_time))
    
    return requests.get(url, params=params, headers=auth_headers)

def request_api(path, params={}):
    return rated_request('https://api.twitter.com/1.1/' + path, params=params)

def paginate_api(path, property_name, start_params={}):
    response = request_api(path, params=start_params)
    params = start_params.copy()
    while response.status_code == 200:
        data = response.json()
        for item in data[property_name]:
            yield item

        next_cursor = data['next_cursor_str']
        if next_cursor != '0':
            params['cursor'] = next_cursor
            response = request_api(path, params=params)
        else: break

def grouper(iterable, n):
    args = [iter(iterable)] * n
    for group in itertools.zip_longest(*args, fillvalue=None):
        yield filter(lambda x: x, group)



def request_users(users):
    return request_api('users/lookup.json',
            params={'screen_name' : ','.join(users)})

def get_users(users):
    for group in grouper(users, 90):
        response = request_users(group)
        if response.status_code == 200:
            for user in response.json():
                yield user

def store_user(user, cursor):
    id_num = user.get('id')

    name = user.get('name', None)
    if name == '': name = None

    location = user.get('location', None)
    if location == '': location = None

    url = user.get('url', None)
    if url == '': url = None

    screen_name = user.get('screen_name')

    values = (id_num, name, location, url, screen_name)
    cursor.execute('INSERT OR IGNORE INTO TwitterUsers VALUES(?,?,?,?,?)', values)

def store_n_common(n, cursor):
    untwittered = cursor.execute('''
            SELECT GU.Login FROM GithubUsers gu
            WHERE gu.id > (
              SELECT max(gu2.id) from TwitterUsers tu
              JOIN GithubUsers gu2
              WHERE gu2.Login = tu.ScreenName)
            ''').fetchmany(n)

    usernames = map(lambda row: row[0], untwittered)
    for user in get_users(usernames):
        store_user(user, cursor)

class User:
    def __init__(self, user_id, screen_name, name=None, location=None, url=None):
        self.user_id = user_id
        self.screen_name = screen_name

        if name == '': self.name = None
        else: self.name = name

        if location == '': self.location = None
        else: self.location = location

        if url == '': self.url = None
        else: self.url = url

    def __repr__(self):
        return 'twitter.User({0}, {1}, name={2}, location={3}, url={4})'.format(
                self.user_id, self.screen_name, self.name, self.location, self.url)

    def __str__(self):
        if self.name == None: return 'TwitterUsers({0}'.format(self.screen_name)
        else: return 'TwitterUsers({0}, {1})'.format(self.screen_name, self.name)

    def from_json(data):
        return User(data['id'], data['screen_name'], data['name'], 
                data['location'], data['url'])

    def _paginate_user_request(path, id_type, items, params={}):
        p = params.copy()
        for group in grouper(items, 90):
            p[id_type] = ','.join(group)
            response = request_api(path, params=p)
            if response.status_code == 200:
                for data in response.json():
                    yield User.from_json(data)



    def fetch_screen_names(screen_names):
        return User._paginate_user_request('users/lookup.json', 'screen_name', screen_names)

    def fetch_single_screen_name(screen_name):
        return next(User.fetch_screen_names([screen_name]))

    def fetch_ids(ids):
        User._paginate_user_request('users/lookup.json', 'user_id', ids)

    def _edge_helper(self, list_type, screen_names=None):
        params = {'screen_name' : self.screen_name,
            'skip_status' : 'true',
            'count': '100',
            'include_user_entities' : 'false' }
        if screen_names: 
            return User._paginate_user_request(
                    list_type + '/list.json', 'screen_name', screen_names, params=params)
                
        else:
            users = paginate_api(list_type + '/list.json', 'users', start_params=params)
            for data in users:
                yield User.from_json(data)


    def followers(self, screen_names=None):
        return self._edge_helper('followers', screen_names)

    def following(self, screen_names=None):
        return self._edge_helper('friends', screen_names)

    def friends(self):
        follower_names = (follower['screen_name'] for follower in self.followers())
        return self.following(follower_names)
