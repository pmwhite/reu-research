import requests
import keys
import itertools
import time
import sqlite3
import twitter
import misc
import rest
from datetime import datetime
from misc import grouper, clean_str_key
from collections import namedtuple
from requests_oauthlib import OAuth1, OAuth2

token_response = requests.post(
        'https://api.twitter.com/oauth2/token?grant_type=client_credentials',
        auth=(keys.TWITTER_CONSUMER_KEY, keys.TWITTER_CONSUMER_SECRET)).json()

_bearer_token = token_response['access_token']
_app_auth = OAuth2(token=token_response)
_user_auth = OAuth1(
        keys.TWITTER_CONSUMER_KEY,
        keys.TWITTER_CONSUMER_SECRET,
        keys.TWITTER_ACCESS_TOKEN_KEY,
        keys.TWITTER_ACCESS_TOKEN_SECRET)

def rated_request(path, params, auth=_app_auth):
    def make_request():
        return rest.cached_get(
                'https://api.twitter.com/1.1/' + path, 
                params=params, auth=auth)
    def extract_rate_info(response):
        headers = response.headers
        try:
            reset_time = int(headers['x-rate-limit-reset']) + 14410
            requests_left = int(headers['x-rate-limit-remaining'])
            return (reset_time, requests_left)
        except:
            return (datetime.utcnow().timestamp() + 5, 1)
    return misc.rated_request(make_request, extract_rate_info)

def paginate_api(path, page_property, params):
    def make_request(cursor):
        p = params.copy()
        c = cursor
        if cursor is None:
            c = -1
        p['cursor'] = c
        return rated_request(path, p)
    def extract_cursor(response):
        print(response.status_code, response.json())
        cursor = response.json()['next_cursor_str']
        if cursor != '0':
            return cursor
    def extract_items(response):
        for item in response.json()[page_property]:
            yield item
    return misc.paginate_api(make_request, extract_cursor, extract_items)

User = namedtuple('User', 'id screen_name name location url follower_count following_count')
Tweet = namedtuple('Tweet', 'id user_id created_at hashtags')

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
        response = rated_request('users/lookup.json', {'screen_name' : ','.join(group)})
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
        response = rated_request('users/lookup.json', {'user_id' : ','.join(group)})
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
        path='followers/ids.json', page_property='ids', params=params))
    following_ids = set(paginate_api(
        path='friends/ids.json', page_property='ids', params=params))
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

def user_degree(user, conn):
    return len(user_friends(user, conn))

def parse_date(date_str):
    return datetime.strptime(date_str, '%a %b %d %H:%M:%S +0000 %Y')

def tweet_from_json(data):
    return Tweet(
            id=data['id'],
            user_id=data['user']['id'],
            created_at=parse_date(data['created_at']),
            hashtags={obj['text'] for obj in data['entities']['hashtags']})

def user_tweets_api(user):
    base_params = {
            'user_id': user.id, 
            'trim_user': True, 
            'count': 200, 
            'include_rts': False,
            'exclude_replies': True, 
            'trim_user': True}
    def make_request(cursor):
        params = base_params.copy()
        if cursor is not None:
            params['max_id'] = cursor
        response = rated_request('statuses/user_timeline.json', params)
        return response
    def extract_cursor(response):
        items = response.json()
        if items != []:
            lowest_id = min([item['id'] for item in items])
            return lowest_id - 1
    def extract_items(response):
        return (tweet_from_json(data) for data in response.json())
    return misc.paginate_api(make_request, extract_cursor, extract_items)

def search_users_api(query):
    def make_request(cursor):
        c = cursor
        if cursor is None:
            c = '1'
        response = rated_request('users/search.json', {'page': c, 'count': 20, 'q': query}, auth=_user_auth)
        print(response.status_code, response.headers)
        return response
    def extract_cursor(response):
        return None
    def extract_items(response):
        return (user_from_json(data) for data in response.json())
    return misc.paginate_api(make_request, extract_cursor, extract_items)


def user_tweets_db(user, conn):
    rows = conn.execute(
            'SELECT * FROM TwitterTweets WHERE UserId = ?',
            (user.id,))
    for (tweet_id, user_id, created_at) in rows:
        tags = {tag for (tag,) in conn.execute(
            'SELECT Tag FROM TwitterTagging WHERE TweetId = ?',
            (tweet_id,))}
        yield Tweet(
                id=tweet_id,
                user_id=user_id,
                created_at=datetime.utcfromtimestamp(created_at),
                hashtags=tags)

def store_tweet(tweet, conn):
    conn.execute(
            'INSERT INTO TwitterTweets VALUES(?,?,?)',
            (tweet.id, tweet.user_id, tweet.created_at.timestamp()))
    for tag in tweet.hashtags:
        conn.execute('INSERT INTO TwitterTagging VALUES(?,?)',
                (tweet.id, tag))

def user_tweets(user, conn):
    return misc.cached_search(
            entity=user,
            db_search=user_tweets_db,
            global_search=lambda user, conn: user_tweets_api(user),
            store=lambda _, tweet, conn: store_tweet(tweet, conn),
            search_type='twitter:tweet',
            conn=conn)
