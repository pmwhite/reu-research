import requests
import keys
import itertools
import time
import storage
import sqlite3

token_reponse = requests.post(
        'https://api.twitter.com/oauth2/token?grant_type=client_credentials',
        auth=(keys.TWITTER_API, keys.TWITTER_SECRET)).json()

access_token = token_reponse['access_token']
auth_headers = {'Authorization': 'Bearer ' + access_token}

def request_users(users):
    rate_limit_state = requests.get(
            'https://api.twitter.com/1.1/application/rate_limit_status.json?resources=users',
            headers=auth_headers).json()['resources']['users']['/users/lookup']

    time_before_reset = max(0.5, int(rate_limit_state['reset']) - time.time())
    requests_left = int(rate_limit_state['remaining'])
    
    if requests_left <= 1: delay_time = time_before_reset + 5
    else: delay_time = time_before_reset / requests_left

    time.sleep(delay_time)
    return requests.get(
        'https://api.twitter.com/1.1/users/lookup.json?screen_name=' + 
        ','.join(users),
        headers=auth_headers)

# Groups an iterable into chunks of size n.
def grouper(iterable, n):
    args = [iter(iterable)] * n
    return itertools.zip_longest(*args, fillvalue='phil')

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
