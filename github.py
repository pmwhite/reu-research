import requests
import time

# Returns an iterator of the names of all github users, in the order of
# their creation. Takes a since parameter so that we can begin where we left
# off if the program crashes or we stop it somehow.
def users_after(last_user, key):
    # We keep track of the last user id that we processed. This is how GitHub
    # manages paging; every new request specifies the user id that ended the
    # previous response.
    last_user_response = requests.get(
            'https://api.github.com/users/' + last_user + 
            '?access_token=' + key).json()
    last_id = str(last_user_response['id'])
    print('Starting from \"' + last_user + '\" - id: ' + last_id)

    # Returns the response to a request for more users; takes no parameters
    # because it looks at last_id and GITHUB_KEY for it's REST parameters.
    def req():
        return requests.get(
            'https://api.github.com/users?since=' + last_id +
            '&access_token=' + key)

    # Begin with a request to start things off
    response = req()

    # Continue iterating while the response is happy.
    while response.status_code == 200:

        # Yield the name of each user in the response.
        for user in response.json():
            last_id = str(user['id'])
            yield user['login']

        # Calculate the time we should wait before making another request.
        # Notice that since this is an iterator, we are not guarunteed to be
        # running at full speed, so we must check how long we took. Perhaps
        # this isn't entirely necessary, but it may be helpful in the future.
        time_before_reset = max(0.5, int(response.headers['X-RateLimit-Reset']) - time.time())
        requests_left = int(response.headers['X-RateLimit-Remaining'])
        delay_time = max(0, time_before_reset / requests_left)

        # Delay until the next request; we leave a little bit of extra time
        # for the last request so that we don't get any off-by-one or latency
        # related errors.
        if requests_left == 1:
            time.sleep(time_left + 5)
        else:
            time.sleep(delay_time)
        response = req()
