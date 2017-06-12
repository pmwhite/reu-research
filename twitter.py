import requests
import keys
import itertools
import time

def get_token(client_key, secret_key):
    token_reponse = requests.post(
            'https://api.twitter.com/oauth2/token?grant_type=client_credentials',
            auth=(client_key, secret_key)).json()
    return token_reponse['access_token']

def get_users(users, access_token):
    auth_headers = {'Authorization': 'Bearer ' + access_token}
    rate_limit_state = requests.get(
            'https://api.twitter.com/1.1/application/rate_limit_status.json?resources=users',
            headers=auth_headers).json()['resources']['users']['/users/lookup']

    time_before_reset = max(0.5, int(rate_limit_state['reset']) - time.time())
    requests_left = int(rate_limit_state['remaining'])
    delay_time = time_before_reset / requests_left
    
    if requests_left == 1:
        time.sleep(time_before_reset + 5)
    else:
        time.sleep(delay_time)

    response = requests.get(
        'https://api.twitter.com/1.1/users/lookup.json?screen_name=' + ','.join(users),
        headers=auth_headers)

    if response.status_code == 200:
        for item in response.json():
            yield item['screen_name']
