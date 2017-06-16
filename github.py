import requests
import time
import sqlite3
import itertools
import keys
import re

def rated_request(url, params={}):
    rate_limit_info = requests.get(
            'https://api.github.com/rate_limit?access_token=' + 
            keys.GITHUB_KEY).json()

    time_before_reset = int(rate_limit_info['rate']['reset']) - time.time()
    requests_left = int(rate_limit_info['rate']['remaining'])
    
    if requests_left <= 1: delay_time = time_before_reset + 5
    else: delay_time = time_before_reset / requests_left

    time.sleep(delay_time)

    request_params = params.copy()
    request_params['access_token'] = keys.GITHUB_KEY
    return requests.get(url, params=request_params)
    

def request_api(path, params={}):
    return rated_request('https://api.github.com/' + path, params = params)

# Returns an iterator through the items in REST listing endpoint. Deals with
# pagination automatically.
def paginate_api(path, start_params={}):
    response = request_api(path, params=start_params)

    def next_page_link():
        link = response.headers.get('Link', None)
        if link == None:
            return None
        else: return re.findall('<(.*?)>', link)[0].strip('<').strip('>')

    # Store the first link to the next page; by keeping this information, we
    # can detect when we have reached the end of all the pages. This prevents
    # looping around forever.
    next_page_url = next_page_link()
    first_link = next_page_url

    while response.status_code == 200:
        # Yield all the items in the currect page
        for item in response.json():
            yield item

        # Get the next page
        if not next_page_url: break
        response = rated_request(next_page_url)
        next_page_url = next_page_link()

        # Break if the next page is actually the first page.
        if next_page_url == first_link:
            break


def users_after(since_id):
    response = request_api('users', params={'since': since_id})
    last_id = since_id
    while response.status_code == 200:
        for user in response.json():
            last_id = user['id']
            yield user
        response = request_api('users', params={'since': last_id})

def full_user(login):
    return request_api('users/' + login).json()

def store_shallow(user, cursor):
    values = (user['id'], user['login'])
    cursor.execute('''
        INSERT INTO GithubUsers (Id, Login)
        VALUES(?, ?)
        ''', values)

def fill_login(login, cursor):
    user = full_user(login)

    username = user['login']

    location = user.get('location', None)
    if location == '': location = None

    email = user.get('email', None)
    if email == '': email = None

    name = user.get('name', None)
    if name == '': name = None

    blog = user.get('blog', None)
    if blog == '': blog = None

    company = user.get('company', None)
    if company == '': company = None

    values = (username, location, email, name, blog, company, user['id'])
    cursor.execute('''
        UPDATE GithubUsers 
        SET Login = ?, Location = ?, Email = ?, Name = ?, Blog = ?, Company = ?
        WHERE Id = ?
        ''', values)

def store_users(users, cursor): 
    for user in users: store_shallow(user, cursor)

def store_n(n, cursor):
    last_id = str(cursor.execute('SELECT MAX(Id) FROM GithubUsers').fetchone()[0])
    if last_id == None: last_id = "0"
    
    for user in itertools.islice(users_after(last_id), n):
        store_shallow(user, cursor)

def fill_n_common(n, cursor):
    unfilled_common = cursor.execute('''
        SELECT Login FROM GithubUsers gu
        JOIN TwitterUsers tu
        WHERE lower(gu.Login) = lower(tu.ScreenName)
        AND gu.Id > (
            SELECT max(gu2.id) FROM GithubUsers gu2
            WHERE gu2.Location is NOT NULL
            OR gu.Email is NOT NULL
            OR gu.Name is NOT NULL
            OR gu.Blog is NOT NULL
            OR gu2.Company is NOT NULL)
        ''').fetchmany(n)

    for row in unfilled_common:
        github.fill_login(row[0], cursor)


class User:
    def __init__(self, user_id, login, 
            location=None, email=None, name=None, 
            blog=None, company=None):

        self.user_id = user_id
        self.login = login

        if location == '': self.location = None
        else: self.location = location

        if email == '': self.email = None
        else: self.email = email

        if name == '': self.name = None
        else: self.name = name

        if blog == '': self.blog = None
        else: self.blog = blog

        if company == '': self.company = None
        else: self.company = company

    def __repr__(self):
        return 'User({0}, {1}, location={2}, email={3}, name={4}, blog={5}, company={6})'.format(
                self.user_id, self.login, self.location, self.email, 
                self.name, self.blog, self.company)

    def __str__(self): 
        if self.name == None:
            return 'User({0})'.format(self.login)
        else: return 'User({0}, {1})'.format(self.login, self.name)

    def from_json(data):
        return User(data['id'], data['login'],
                location=data.get('location', None),
                email=data.get('email', None),
                name=data.get('name', None),
                blog=data.get('blog', None),
                company=data.get('company', None))

    def fetch_single(login):
        response = request_api('users/' + login)
        if response.status_code == 200: 
            return User.from_json(response.json())
        else: return None

    def refetch(self):
        return User.fetch_single(self.login)

    def fetch_after(since_id):
        response = request_api('users', params={'since': since_id})
        last_id = since_id
        while response.status_code == 200:
            for user in response.json():
                last_id = user['id']
                yield User.from_json(user)
            response = request_api('users', params={'since': last_id})

    def store(self, cursor):
        values = (self.user_id, self.login, self.location, self.email, 
                self.name, self.blog, self.company)

        cursor.execute('REPLACE INTO GithubUsers VALUES(?,?,?,?,?,?,?)', values)

    def repos(self):
        items = paginate_api('users/' + self.login + '/repos')
        # Filter on whether the repo is a fork or not
        return map(Repo.from_json, items)

class Repo:
    def __init__(self, repo_id, name, owner_login, language, is_fork, homepage=None):
        self.repo_id = repo_id
        self.name = name
        self.owner_login = owner_login
        self.language = language

        if homepage == '': self.homepage = None
        else: self.homepage = homepage
        self.is_fork = is_fork

    def __repr__(self):
        return 'Repo({0}, {1}, {2}, {3}, {4})'.format(
                self.repo_id, self.name, self.language, 
                self.homepage, self.is_fork)

    def __str__(self):
        if self.homepage == None:
            return 'Repo({0}/{1}, {2})'.format(
                    self.owner_login, self.name, self.language)
        else: return 'Repo({0}/{1}, {2}, {3})'.format(
                self.owner_login, self.name, self.language, self.homepage)

    def from_json(data):
        return Repo(data['id'], data['name'], data['owner']['login'], 
                data['language'], data['fork'], homepage=data['homepage'])

    def fetch(owner_login, repo_name):
        response = request_api('repos/' + owner_login + '/' + repo_name)
        if response.status_code == 200:
            return Repo.from_json(response.json())
        else: return None

    def contributors(self):
        response = requests_api(
                'repos/' + self.owner_login + '/' + self.name + '/contributors')
        return map(User.from_json, response.json())
