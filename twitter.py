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
    cursor.execute('INSERT OR IGNORE INTO TwitterUsers VALUES(?,?,?,?,?)',
            values)

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

    def __init__(self, user_id, screen_name, name, 
            location, url, follower_count, following_count, is_searched, conn):
        self.user_id = user_id
        self.screen_name = screen_name
        if name == '': self.name = None
        else: self.name = name
        if location == '': self.location = None
        else: self.location = location
        if url == '': self.url = None
        else: self.url = url
        self.follower_count = follower_count
        self.following_count = following_count
        self.is_searched = is_searched
        self.store(conn)

    def __repr__(self):
        return 'twitter.User(user_id={0}, screen_name={1}, name={2}, location={3}, url={4})'.format(
                self.user_id, self.screen_name, self.name, self.location, self.url)

    def __str__(self):
        if self.name == None: return 'TwitterUsers({0})'.format(self.screen_name)
        else: return 'TwitterUsers({0}, {1})'.format(self.screen_name, self.name)

    def __hash__(self):
        return self.user_id

    def __eq__(self, other):
        return self.user_id == other.user_id

    def to_json(self):
        props = [('id', self.user_id),
                 ('screenName', self.screen_name),
                 ('name', self.name),
                 ('location', self.location),
                 ('url', self.url)]
        return dict((k, v) for k, v in props if v is not None)

    def from_json(data, conn):
        return User(
                user_id=data['id'], 
                screen_name=data['screen_name'], 
                name=data['name'], 
                location=data['location'], 
                url=data['url'],
                follower_count=data['followers_count'],
                following_count=data['friends_count'],
                is_searched=0,
                conn=conn)

    def fetch_screen_names(screen_names, conn):
        unretrieved = []
        retrieved = []
        for screen_name in screen_names:
            db_response = conn.execute(
                    'SELECT * FROM TwitterUsers WHERE ScreenName COLLATE NOCASE = ?',
                    (screen_name,)).fetchone()
            if db_response is not None: retrieved.append(User(*db_response, conn))
            else: unretrieved.append(screen_name)
        for group in grouper(unretrieved, 100):
            response = rated_request('users/lookup.json', 
                    {'screen_name' : ','.join(group)},
                    family='users',
                    resource='/users/lookup')
            if response.status_code == 200:
                for data in response.json():
                    retrieved.append(User.from_json(data, conn=conn))
        return retrieved

    def fetch_ids(ids, conn):
        unretrieved = []
        retrieved = []
        for user_id in ids:
            db_response = conn.execute(
                    'SELECT * FROM TwitterUsers WHERE Id = ?',
                    (user_id,)).fetchone()
            if db_response is not None: retrieved.append(User(*db_response, conn))
            else: unretrieved.append(user_id)
        for group in grouper(unretrieved, 100):
            response = rated_request('users/lookup.json', 
                    {'user_id' : ','.join(group)},
                    family='users',
                    resource='/users/lookup')
            if response.status_code == 200:
                for data in response.json():
                    retrieved.append(User.from_json(data, conn=conn))
        return retrieved

    def fetch_single_screen_name(screen_name, conn):
        return User.fetch_screen_names([screen_name], conn)[0]

    def friends(self, conn):
        if self.is_searched:
            rows = conn.execute(
                    'SELECT ToId FROM TwitterFriendships WHERE FromId = ?',
                    (self.user_id,)).fetchall()
            backward_rows = conn.execute(
                    'SELECT FromId FROM TwitterFriendships WHERE ToId = ?',
                    (self.user_id,)).fetchall()
            rows.extend(backward_rows)
            result = []
            for row in rows:
                db_response = conn.execute(
                        'SELECT * FROM TwitterUsers WHERE Id = ?', 
                        row).fetchone()
                result.append(User(*db_response, conn))
            return result
        else:
            params = {'screen_name' : self.screen_name,
                    'stringify_ids': 'true'}
            follower_ids = set(paginate_api(
                path='followers/ids.json', 
                page_property='ids', 
                params=params,
                family='followers',
                resource='/followers/ids'))
            following_ids = set(paginate_api(
                path='friends/ids.json', 
                page_property='ids', 
                params=params,
                family='friends',
                resource='/friends/ids'))
            common_ids = follower_ids.intersection(following_ids)
            for friend_id in common_ids:
                conn.execute(
                        'INSERT OR REPLACE INTO TwitterFriendships VALUES(?,?)',
                        (self.user_id, friend_id))
            users = User.fetch_ids(common_ids, conn)
            self.is_searched = 1
            self.store(conn)
            conn.commit()
            return users

    def store(self, conn):
        values = (self.user_id, self.screen_name, self.name, 
                self.location, self.url, self.follower_count, 
                self.following_count, self.is_searched)
        conn.execute('REPLACE INTO TwitterUsers VALUES(?,?,?,?,?,?,?,?)', values)
