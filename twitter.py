"""Important module for handling Twitter API requests. Rate limiting is handled
automatically, and caching is used heavily to speed up the process."""
import misc
import requests
import keys
import rest
from network import Walk
from visualization import GexfWritable, CsvWritable
from datetime import datetime
from rest import grouper, clean_str_key
from collections import namedtuple
from requests_oauthlib import OAuth1, OAuth2
from itertools import islice

_token_response = None
def token_response():
"""Gets an OAuth token for making API requests. If the global variable has
already been set, it will be returned without re-obtaining it."""
    global _token_response
    if _token_response is None:
        _token_response = requests.post(
                'https://api.twitter.com/oauth2/token?grant_type=client_credentials',
                auth=(keys.TWITTER_CONSUMER_KEY, keys.TWITTER_CONSUMER_SECRET)).json()
    return _token_response

def _app_auth():
"Returns the application-only authentication object."
    return OAuth2(token=token_response())

def _user_auth():
"Returns user-specific authentication."
    return OAuth1(
            keys.TWITTER_CONSUMER_KEY,
            keys.TWITTER_CONSUMER_SECRET,
            keys.TWITTER_ACCESS_TOKEN_KEY,
            keys.TWITTER_ACCESS_TOKEN_SECRET)

def rated_request(path, params, conn, rate_family, auth=_app_auth()):
"""Makes a twitter API requests while respecting rate limits. Since Twitter has
a number of different rate limits for different types of requests, a
rate_family parameter is used to separate one from the other."""
    def make_request():
        return rest.cached_get(
                conn=conn,
                rate_family=rate_family,
                path='https://api.twitter.com/1.1/' + path, 
                params=params, 
                auth=auth)
    def extract_rate_info(response):
        headers = response.headers
        try:
            reset_time = int(headers['x-rate-limit-reset']) + 14410
            requests_left = int(headers['x-rate-limit-remaining'])
            return (reset_time, requests_left)
        except:
            return (datetime.utcnow().timestamp() + 5, 1)
    return rest.rated_request(make_request, extract_rate_info, rate_family=rate_family)

def paginate_api(path, page_property, params, conn, rate_family):
"""Handles paging through a Twitter API request. The `page_property` is the
path to the actual items in the returned object."""
    def make_request(cursor):
        p = params.copy()
        c = cursor
        if cursor is None:
            c = -1
        p['cursor'] = c
        return rated_request(path, p, conn, rate_family)
    def extract_cursor(response):
        cursor = response.json()['next_cursor_str']
        if cursor != '0':
            return cursor
    def extract_items(response):
        for item in response.json()[page_property]:
            yield item
    return rest.paginate_api(make_request, extract_cursor, extract_items)

User = namedtuple('User', 'id screen_name name location url follower_count following_count')
Tweet = namedtuple('Tweet', 'id user_id created_at hashtags')

def user_from_json(data):
"Converts a JSON object to a user object."
    return User(
            id=data['id'],
            screen_name=data['screen_name'].lower(),
            name=clean_str_key(data, 'name'),
            location=clean_str_key(data, 'location'),
            url=clean_str_key(data, 'url'),
            follower_count=clean_str_key(data, 'followers_count'),
            following_count=clean_str_key(data, 'friends_count'))

def user_fetch_screen_names(screen_names, conn):
"Gets a list of users (by username) from either the API or the database."
    result = {sn: None for sn in screen_names}
    for group in grouper(screen_names, 100):
        response = rated_request('users/lookup.json', {'screen_name' : ','.join(group)}, conn, 
                rate_family='twitter_lookup_users')
        if response.status_code == 200:
            for data in response.json():
                user = user_from_json(data)
                result[user.screen_name] = user
    return result

def user_fetch_screen_name(screen_name, conn):
"Gets a single user (by username) from either the API or the database."
    return user_fetch_screen_names([screen_name], conn)[screen_name]

def user_fetch_ids(ids, conn):
"Gets a list of users (by id) from either the API or the database."
    result = {user_id: None for user_id in ids}
    for group in grouper(ids, 100):
        response = rated_request('users/lookup.json', {'user_id' : ','.join(group)}, conn, 
                rate_family='twitter_lookup_users')
        if response.status_code == 200:
            for data in response.json():
                user = user_from_json(data)
                result[user.id] = user
    return result

def user_friends(user, conn):
"Finds the users that a certain user is mutually following."
    params = {'screen_name' : user.screen_name,
            'stringify_ids': 'true'}
    follower_ids = set(paginate_api(
        path='followers/ids.json', page_property='ids', params=params, conn=conn, rate_family='twitter_follower_ids'))
    following_ids = set(paginate_api(
        path='friends/ids.json', page_property='ids', params=params, conn=conn, rate_family='twitter_friend_ids'))
    common_ids = follower_ids.intersection(following_ids)
    return [user for user in user_fetch_ids(common_ids, conn).values() if user is not None]

def parse_date(date_str):
"Parse a Twitter date string."
    return datetime.strptime(date_str, '%a %b %d %H:%M:%S +0000 %Y')

def tweet_from_json(data):
"Convert a JSON object to a tweet object."
    return Tweet(
            id=data['id'],
            user_id=data['user']['id'],
            created_at=parse_date(data['created_at']),
            hashtags={obj['text'] for obj in data['entities']['hashtags']})

def user_tweets(user, conn):
"Gets all the available tweets made by a certain user."
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
        response = rated_request('statuses/user_timeline.json', params, conn, 
                rate_family='twitter_user_tweets')
        return response
    def extract_cursor(response):
        items = response.json()
        if items != []:
            lowest_id = min([item['id'] for item in items])
            return lowest_id - 1
    def extract_items(response):
        return (tweet_from_json(data) for data in response.json())
    return rest.paginate_api(make_request, extract_cursor, extract_items)

def activity_histogram(user, num_blocks, conn):
"Compiles an activity histogram based on the times a certain user has tweeted."
    instants = (tweet.created_at for tweet in islice(user_tweets(user, conn), 100))
    return misc.activity_histogram(instants, num_blocks, conn)

def search_users(query):
"Performs a search query against the API on users."
    def make_request(cursor):
        c = cursor
        if cursor is None:
            c = '1'
        response = rated_request('users/search.json', {'page': c, 'count': 20, 'q': query}, conn, auth=_user_auth(),
                rate_family='twitter_search')
        print(response.status_code, response.headers)
        return response
    def extract_cursor(response):
        return None
    def extract_items(response):
        return (user_from_json(data) for data in response.json())
    return rest.paginate_api(make_request, extract_cursor, extract_items)

user_schema = {
        'id': 'string',  
        'screen_name': 'string', 
        'name': 'string',
        'location': 'string',
        'url': 'string',
        'follower_count': 'integer',
        'following_count': 'integer'}

def user_serialize(user):
    return user._asdict()

def user_label(user):
    return user.screen_name

user_gexf = GexfWritable(
        schema=user_schema,
        serialize=user_serialize,
        label=user_label)

user_csv = CsvWritable(
        to_row=lambda user: list(user),
        from_row=lambda row: User(*row),
        cols='id screen_name name location url follower_count following_count'.split(' '))

def user_out_gen(user, conn):
    for friend in user_friends(user, conn):
        yield friend

def user_in_gen(user, conn): 
    return []

def user_select_leaves(leaves, midpoint_radius=25):
    sorted_leaves =  list(sorted(leaves, 
        key=lambda f: max(f.follower_count, f.following_count)))
    midpoint = int(len(sorted_leaves) / 2)
    s = max(midpoint - midpoint_radius, 0)
    e = max(midpoint + midpoint_radius, len(sorted_leaves))
    return sorted_leaves[s:e]

def user_walk(conn):
    return Walk(
            out_gen=lambda user: user_out_gen(user, conn),
            in_gen=lambda user: user_in_gen(user, conn),
            select_leaves=lambda leaves: user_select_leaves(leaves))
