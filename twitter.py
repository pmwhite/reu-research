import requests
import keys
import itertools
import time
import sqlite3
import twitter

from misc import grouper

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
    else: delay_time = min(15, time_before_reset / requests_left)
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

def clean_str(s):
    if s == '': return None
    else: return s

class User:
    def __init__(self, user_id, screen_name, name, 
            location, url, follower_count, following_count, is_searched):
        self.user_id = user_id
        self.screen_name = screen_name
        self.name = clean_str(name)
        self.location = clean_str(location)
        self.url = clean_str(url)
        self.follower_count = follower_count
        self.following_count = following_count
        self.is_searched = is_searched

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

    def from_json(data, is_searched):
        return User(
                user_id=data['id'], 
                screen_name=data['screen_name'], 
                name=data['name'], 
                location=data['location'], 
                url=data['url'],
                follower_count=data['followers_count'],
                following_count=data['friends_count'],
                is_searched=0)

    def fetch_screen_names(screen_names, conn):
        unretrieved = []
        for screen_name in screen_names:
            db_response = conn.execute(
                    'SELECT * FROM TwitterUsers WHERE ScreenName COLLATE NOCASE = ?',
                    (screen_name,)).fetchone()
            if db_response is not None:
                yield User(*db_response)
            else:
                unretrieved.append(screen_name)
        for group in grouper(unretrieved, 100):
            response = rated_request('users/lookup.json', 
                    {'screen_name' : ','.join(group)},
                    family='users',
                    resource='/users/lookup')
            if response.status_code == 200:
                for data in response.json():
                    user = User.from_json(data, is_searched=0)
                    user.ensure_storage(conn)
                    yield user

    def db_fetch_id(user_id, conn):
        db_response = conn.execute(
                'SELECT * FROM TwitterUsers WHERE Id = ?',
                (user_id,)).fetchone()
        if db_response is not None: 
            return User(*db_response)


    def fetch_ids(ids, conn):
        unretrieved = []
        for user_id in ids:
            user = User.db_fetch_id(user_id, conn)
            if user is not None: 
                yield user
            else: 
                unretrieved.append(user_id)
        for group in grouper(unretrieved, 100):
            response = rated_request('users/lookup.json', 
                    {'user_id' : ','.join(group)},
                    family='users',
                    resource='/users/lookup')
            if response.status_code == 200:
                for data in response.json():
                    user = User.from_json(data, is_searched=0)
                    user.ensure_storage(conn)
                    yield user

    def fetch_single_screen_name(screen_name, conn):
        return next(User.fetch_screen_names([screen_name], conn))

    def friends(self, conn):
        if self.is_searched:
            rows = conn.execute(
                    'SELECT ToId FROM TwitterFriendships WHERE FromId = ?',
                    (self.user_id,)).fetchall()
            backward_rows = conn.execute(
                    'SELECT FromId FROM TwitterFriendships WHERE ToId = ?',
                    (self.user_id,)).fetchall()
            rows.extend(backward_rows)
            unfetched = []
            for row in set(rows):
                db_response = conn.execute(
                        'SELECT * FROM TwitterUsers WHERE Id = ?', 
                        row).fetchone()
                try:
                    yield User(*db_response)
                except:
                    unfetched.append(str(row[0]))
            for x in User.fetch_ids(unfetched, conn):
                print(x)
                yield x
            conn.commit()
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
                        'INSERT INTO TwitterFriendships VALUES(?,?)',
                        (self.user_id, friend_id))
            for user in User.fetch_ids(common_ids, conn):
                user.ensure_storage(conn)
                yield user
            self.is_searched = 1
            conn.execute(
                    'UPDATE TwitterUsers SET IsSearched = 1 WHERE Id = ?',
                    (self.user_id,))
            conn.commit()

    def ensure_storage(self, conn):
        values = (self.user_id, self.screen_name, self.name, 
                self.location, self.url, self.follower_count, 
                self.following_count, self.is_searched)
        conn.execute('INSERT OR IGNORE INTO TwitterUsers VALUES(?,?,?,?,?,?,?,?)', values)
