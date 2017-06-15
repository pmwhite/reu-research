import requests
import time
import sqlite3
import itertools
import keys

rate_limit_reset = None
requests_left = None

def request_api(path, params={}):
    global rate_limit_reset
    global requests_left
    if rate_limit_reset != None:
        time_left = rate_limit_reset - time.time()
        delay_time = max(0, time_left / requests_left)
        if requests_left == 1:
            time.sleep(delay_time + 4)
        else:
            time.sleep(delay_time)
    request_params = params.copy()
    request_params['access_token'] = keys.GITHUB_KEY
    response = requests.get(
            'https://api.github.com/' + path,
            params = request_params)

    rate_limit_reset = int(response.headers['X-RateLimit-Reset'])
    requests_left = int(response.headers['X-RateLimit-Remaining'])

    return response

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
        values = (self.user_id, self.username, self.location, self.email, 
                self.name, self.blog, self.company)

        cursor.execute('REPLACE INTO GithubUsers VALUES(?,?,?,?,?,?,?)', values)
