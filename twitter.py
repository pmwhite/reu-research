import requests
import keys
import itertools
import time
import sqlite3
import twitter
import misc
from misc import grouper, clean_str_key
from collections import namedtuple

token_reponse = requests.post(
        'https://api.twitter.com/oauth2/token?grant_type=client_credentials',
        auth=(keys.TWITTER_API, keys.TWITTER_SECRET)).json()

access_token = token_reponse['access_token']
auth_headers = {'Authorization': 'Bearer ' + access_token}

def rated_request(path, params, family, resource):
    def make_request():
        return requests.get(
                'https://api.twitter.com/1.1/' + path, 
                params=params, headers=auth_headers)
    def extract_rate_info(response):
        headers = response.headers
        try:
            reset_time = int(headers['x-rate-limit-reset']) + 14410
            requests_left = int(headers['x-rate-limit-remaining'])
            return (reset_time, requests_left)
        except:
            print(reponse.headers)
            print(response.json())
            raise 'issues with rate limit'
    return misc.rated_request(make_request, extract_rate_info)

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

User = namedtuple('User', 'id screen_name name location url follower_count following_count')

# User -> Dict
def user_to_json(user):
    return {'id': user.id,
            'screenName': user.screen_name,
            'name': user.name,
            'location': user.location,
            'url': user.url,
            'followerCount': user.follower_count,
            'followingCount': user.following_count}

# Dict -> User
def user_from_json(data):
    return User(
            id=data['id'],
            screen_name=data['screen_name'].lower(),
            name=clean_str_key(data, 'name'),
            location=clean_str_key(data, 'location'),
            url=clean_str_key(data, 'url'),
            follower_count=clean_str_key(data, 'followers_count'),
            following_count=clean_str_key(data, 'friends_count'))

# User -> DB -> Unit
def store_user(user, conn):
    values = (user.id, user.screen_name, user.name, 
            user.location, user.url, user.follower_count, 
            user.following_count)
    conn.execute('INSERT OR IGNORE INTO TwitterUsers VALUES(?,?,?,?,?,?,?)', values)

# String list -> DB -> Map<String, User option>
def user_fetch_screen_names_db(screen_names, conn):
    return misc.fetch_many_db(
            query='SELECT * FROM TwitterUsers WHERE ScreenName COLLATE NOCASE = ?',
            identifiers=screen_names,
            entity_creator=User,
            conn=conn)

# String list -> Map<String, User option>
def user_fetch_screen_names_api(screen_names):
    result = {sn: None for sn in screen_names}
    for group in grouper(screen_names, 100):
        response = rated_request('users/lookup.json', 
                {'screen_name' : ','.join(group)},
                family='users',
                resource='/users/lookup')
        if response.status_code == 200:
            for data in response.json():
                user = user_from_json(data)
                result[user.screen_name] = user
    return result

# String list -> DB -> Map<String, User option>
def user_fetch_screen_names(screen_names, conn):
    return misc.cached_fetch(
            db_query='SELECT * FROM TwitterUsers WHERE ScreenName COLLATE NOCASE = ?',
            api_fetch_many=user_fetch_screen_names_api,
            from_db=User,
            from_json=user_from_json,
            store=store_user,
            identifiers=screen_names,
            conn=conn)

# String -> DB -> User option
def user_fetch_screen_name(screen_name, conn):
    return user_fetch_screen_names([screen_name], conn)[screen_name]

# String list -> Map<String, User option>
def user_fetch_ids_api(ids):
    result = {user_id: None for user_id in ids}
    for group in grouper(ids, 100):
        response = rated_request('users/lookup.json', 
                {'user_id' : ','.join(group)},
                family='users',
                resource='/users/lookup')
        if response.status_code == 200:
            for data in response.json():
                user = user_from_json(data)
                result[user.id] = user
    return result

# String list -> DB -> Map<String, User option>
def user_fetch_ids(ids, conn):
    return misc.cached_fetch(
            db_query='SELECT * FROM TwitterUsers WHERE Id = ?',
            api_fetch_many=user_fetch_ids_api,
            from_db=User,
            from_json=user_from_json,
            store=store_user,
            identifiers=ids,
            conn=conn)

def user_friends_db(user, conn):
    rows = conn.execute('''
            SELECT ToId FROM TwitterFriendships WHERE FromId = ?
            UNION
            SELECT FromId FROM TwitterFriendships WHERE ToId = ?
            ''', (user.id, user.id))
    ids = [user_id for (user_id,) in rows]
    return [user for user in user_fetch_ids(ids, conn).values() if user is not None]

def user_friends_api(user, conn):
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
    return [user for user in user_fetch_ids(common_ids, conn).values() if user is not None]

def store_user_friend(user, friend, conn):
    conn.execute(
            'INSERT INTO TwitterFriendships VALUES(?,?)',
            (user.id, friend.id))
    store_user(friend, conn)

def user_friends(user, conn):
    return misc.cached_search(
            entity=user,
            db_search=user_friends_db,
            global_search=user_friends_api,
            store=store_user_friend,
            search_type='twitter:friend',
            conn=conn)
