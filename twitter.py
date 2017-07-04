import requests
import keys
import itertools
import time
import sqlite3
import twitter
import misc
from misc import grouper, clean_str
from collections import namedtuple

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

User = namedtuple('User', 'id screen_name name location url follower_count following_count')

def user_to_json(user):
    props = [('id', user.id),
                ('screenName', user.screen_name),
                ('name', user.name),
                ('location', user.location),
                ('url', user.url),
                ('followerCount', user.follower_count),
                ('followingCount', user.following_count)]
    return dict((k, v) for k, v in props if v is not None)

def user_from_json(data):
    return User(
            id=data['id'],
            screen_name=data['screen_name'],
            name=data['name'],
            location=data['location'],
            url=data['url'],
            follower_count=data['followers_count'],
            following_count=data['friends_count'])

def store_user(user, conn):
    values = (user.id, user.screen_name, user.name, 
            user.location, user.url, user.follower_count, 
            user.following_count)
    conn.execute('INSERT OR IGNORE INTO TwitterUsers VALUES(?,?,?,?,?,?,?)', values)

def user_fetch_screen_name_db(screen_name, conn):
    print(screen_name)
    db_response = conn.execute(
            'SELECT * FROM TwitterUsers WHERE ScreenName COLLATE NOCASE = ?',
            (screen_name,)).fetchone()
    if db_response is not None:
        return User(*db_response)

def user_fetch_screen_names_api(screen_names):
    for group in grouper(screen_names, 100):
        response = rated_request('users/lookup.json', 
                {'screen_name' : ','.join(group)},
                family='users',
                resource='/users/lookup')
        if response.status_code == 200:
            for data in response.json():
                yield user_from_json(data)

def user_fetch_screen_names(screen_names, conn):
    unretrieved = []
    print(screen_names)
    for screen_name in screen_names:
        user = user_fetch_screen_name_db(screen_name, conn)
        if user is not None:
            yield user
        else:
            unretrieved.append(screen_name)
    for user in user_fetch_screen_names_api(unretrieved):
        store_user(user, conn)
        yield user

def user_fetch_screen_name(screen_name, conn):
    return next(user_fetch_screen_names([screen_name], conn))

def user_fetch_id_db(user_id, conn):
    db_response = conn.execute(
            'SELECT * FROM TwitterUsers WHERE Id = ?',
            (user_id,)).fetchone()
    if db_response is not None: 
        return User(*db_response)

def user_fetch_ids_api(ids):
    for group in grouper(ids, 100):
        response = rated_request('users/lookup.json', 
                {'user_id' : ','.join(group)},
                family='users',
                resource='/users/lookup')
        if response.status_code == 200:
            for data in response.json():
                yield user_from_json(data)

def user_fetch_ids(ids, conn):
    unretrieved = []
    for user_id in ids:
        user = user_fetch_id_db(user_id, conn)
        if user is not None: 
            yield user
        else: 
            unretrieved.append(user_id)
    for user in user_fetch_ids_api(unretrieved):
        store_user(user, conn)
        yield user

def user_friends_db(user, conn):
    rows = conn.execute(
            'SELECT ToId FROM TwitterFriendships WHERE FromId = ?',
            (user.id,)).fetchall()
    backward_rows = conn.execute(
            'SELECT FromId FROM TwitterFriendships WHERE ToId = ?',
            (user.id,)).fetchall()
    rows.extend(backward_rows)
    for (user_id,) in set(rows):
        user = user_fetch_id_db(user_id, conn)
        if user is None:
            print(user_id)
        yield user

def user_friends_api(user):
    params = {'screen_name' : user.screen_name,
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
    for user in user_fetch_ids_api(common_ids):
        yield user

def store_user_friend(user, friend, conn):
    conn.execute(
            'INSERT INTO TwitterFriendships VALUES(?,?)',
            (user.id, friend.id))
    store_user(friend, conn)


user_friends = misc.CachedSearch(
        db_fetch=user_friends_db,
        api_fetch=user_friends_api,
        store=store_user_friend,
        search_type='twitter:friend')
