import requests
import itertools
import redis
import twitter
import github
import keys

r = redis.StrictRedis(host='localhost', port=6379, db=0)

def github_stack_users():
    last_user = r.get('last_common').decode()
    stack_users = set(map(lambda line: line.strip(), open('users_stack.txt', 'r')))
    for github_user in github.usernames_after(last_user, keys.GITHUB_KEY):
        if github_user in stack_users:
            yield github_user

# Groups an iterable into chunks of size n.
def grouper(iterable, n):
    args = [iter(iterable)] * n
    return itertools.zip_longest(*args, fillvalue='phil')

def github_stack_twitter_users():
    access_token = twitter.get_token(keys.TWITTER_API, keys.TWITTER_SECRET)
    for github_user_chunks in grouper(github_stack_users(), 90):
        for user in twitter.get_users(github_user_chunks, access_token):
            yield user

pipe = r.pipeline()
count = 0
for user in github_stack_twitter_users():
    pipe.rpush('users:common', user)
    pipe.set('last_common', user)
    pipe.execute()
    count = count + 1
    if count % 50 == 0: print(count)
