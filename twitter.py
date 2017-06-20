import requests
import keys
import itertools
import time
import sqlite3
import twitter

token_reponse = requests.post(
        'https://api.twitter.com/oauth2/token?grant_type=client_credentials',
        auth=(keys.TWITTER_API, keys.TWITTER_SECRET)).json()

access_token = token_reponse['access_token']
auth_headers = {'Authorization': 'Bearer ' + access_token}

def rated_request(path, params, family, resource):
    rate_limit = requests.get(
            'https://api.twitter.com/1.1/application/rate_limit_status.json?' + 
            'resources=' + family,
            headers=auth_headers).json()
    print(rate_limit)
    rate_limit_state = rate_limit['resources'][family][resource]

    time_before_reset = int(rate_limit_state['reset']) - time.time()
    requests_left = int(rate_limit_state['remaining'])

    print('time left:', time_before_reset, ', requests left:', requests_left)
    
    if requests_left <= 1: delay_time = time_before_reset + 5
    else: delay_time = time_before_reset / requests_left

    time.sleep(max(0.5,delay_time))
    
    return requests.get(
            'https://api.twitter.com/1.1/' + path, 
            params=params, headers=auth_headers)

def paginate_api(path, page_property, params, family, resource):
    cursor = -1
    p = params.copy()
    p['cursor'] = cursor
    response = rated_request(path, p, family=family, resource=resource)
    while response.status_code == 200:
        print(cursor)
        data = response.json()
        for item in data[page_property]:
            yield item

        cursor = data['next_cursor_str']
        if cursor == '0': break
        p['cursor'] = cursor
        response = rated_request(path, p, family=family, resource=resource)

def grouper(iterable, n):
    args = [iter(iterable)] * n
    for group in itertools.zip_longest(*args, fillvalue=None):
        yield filter(lambda x: x != None, group)



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

    def _fetch_helper(id_type, items):
        listed = list(items)
        print(items)
        for group in grouper(listed, 100):
            response = rated_request('users/lookup.json', 
                    {id_type : ','.join(group)},
                    family='users',
                    resource='/users/lookup')
            if response.status_code == 200:
                for data in response.json():
                    yield User.from_json(data)



    def fetch_screen_names(screen_names):
        return User._fetch_helper('screen_name', screen_names)

    def fetch_ids(ids):
        return User._fetch_helper('user_id', ids)

    def fetch_single_screen_name(screen_name):
        return next(User.fetch_screen_names([screen_name]))

    def followers(self):
        users = paginate_api(
                path='followers/list.json', 
                page_property='users',
                params={'screen_name': self.screen_name, 'count': 100},
                family='followers', 
                resource='/followers/list')
        for data in users:
            yield User.from_json(data)


    def following(self):
        users = paginate_api(
                path='friends/list.json', 
                page_property='users',
                params={'screen_name': self.screen_name, 'count': 100},
                family='friends', 
                resource='/friends/list')
        for data in users:
            yield User.from_json(data)

    def friends(self):
        params = {'screen_name' : self.screen_name,
                'stringify_ids': 'true'}
        
        follower_ids = set(paginate_api(
            path='followers/ids.json', 
            page_property='ids', 
            params={'screen_name' : self.screen_name, 'stringify_ids' : 'true'},
            family='followers',
            resource='/followers/ids'))

        following_ids = set(paginate_api(
            path='friends/ids.json', 
            page_property='ids', 
            params={'screen_name' : self.screen_name, 'stringify_ids' : 'true'},
            family='friends',
            resource='/friends/ids'))
        common_ids = follower_ids.intersection(following_ids)
        print(following_ids)
        print(follower_ids)
        print(common_ids)
        return User.fetch_ids(list(common_ids))

