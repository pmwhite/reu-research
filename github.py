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

    time.sleep(max(0,5,delay_time))

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

    values = (user['id'], username, location, email, name, blog, company)
    cursor.execute('REPLACE INTO GithubUsers VALUES(?,?,?,?,?,?,?)', values)

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
    def __init__(self, cursor, user_id, login, 
            location=None, email=None, name=None, 
            blog=None, company=None, is_searched=0):

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

        self.is_searched = is_searched

        self.store(cursor)

    def __repr__(self):
        return 'github.User({0}, {1}, location={2}, email={3}, name={4}, blog={5}, company={6})'.format(
                self.user_id, self.login, self.location, self.email, 
                self.name, self.blog, self.company)

    def __str__(self): 
        if self.name == None:
            return 'GithubUser({0})'.format(self.login)
        else: return 'GithubUser({0}, {1})'.format(self.login, self.name)

    def __hash__(self):
        return self.user_id

    def __eq__(self, other):
        return self.user_id == other.user_id

    def to_json(self):
        props = [('id', self.user_id),
                 ('login', self.login),
                 ('location', self.location),
                 ('email', self.email),
                 ('name', self.name),
                 ('blog', self.blog),
                 ('company', self.company)]
        return dict((k, v) for k, v in props if v is not None)

    def from_json(data, cursor):
        return User(cursor, data['id'], data['login'],
                location=data.get('location', None),
                email=data.get('email', None),
                name=data.get('name', None),
                blog=data.get('blog', None),
                company=data.get('company', None))

    def fetch_login(login, cursor):
        db_response = cursor.execute(
                'SELECT * FROM GithubUsers WHERE Login = ?', 
                (login,)).fetchone()

        if db_response: return User(cursor, *db_response)
        else:
            response = request_api('users/' + login)
            if response.status_code == 200: 
                return User.from_json(response.json(), cursor)
            else: return None

    def refetch(self, cursor):
        return User.fetch_single(self.login, cursor)

    def fetch_after(since_id):
            return map(User.from_json,
                    paginate_api('users', start_params={'since': since_id}))

    def repos(self, cursor):
        if self.is_searched != 0:
            db_response = cursor.execute(
                'SELECT * FROM GithubRepos WHERE OwnerId = ?',
                (self.user_id,)).fetchall()
            return [Repo(cursor, *values) for values in db_response]
        else: 
            items = paginate_api('users/' + self.login + '/repos')
            result = [Repo.from_json(cursor, data) for data in items]
            self.is_searched = 1
            self.store(cursor)
            cursor.commit()
            return result

    def store(self, cursor):
        values = (self.user_id, self.login, self.location, 
                self.email, self.name, self.blog, self.company, 
                self.is_searched)
        if self.location or self.email or self.name or self.blog or self.company or self.is_searched:
            cursor.execute('REPLACE INTO GithubUsers VALUES(?,?,?,?,?,?,?,?)', 
                    values)
        else:
            cursor.execute('INSERT OR IGNORE INTO GithubUsers VALUES(?,?,?,?,?,?,?,?)',
                    values)

class Repo:
    def __init__(self, cursor, repo_id, owner_id, owner_login, name, language, is_fork, homepage=None, is_searched=0):

        self.repo_id = repo_id
        self.owner_login = owner_login
        self.name = name
        self.owner_id = owner_id
        self.language = language

        if homepage == '': self.homepage = None
        else: self.homepage = homepage
        self.is_fork = is_fork

        self.is_searched = is_searched

        self.store(cursor)

    def __str__(self):
        return 'Repo({0}/{1}, {2})'.format(
                self.owner_login, self.name, self.language)

    def from_json(cursor, data):
        return Repo(cursor, data['id'], data['owner']['id'], data['owner']['login'], data['name'],
                data['language'], data['fork'], homepage=data['homepage'])

    def fetch(cursor, owner_login, repo_name):
        response = request_api('repos/' + owner_login + '/' + repo_name)
        if response.status_code == 200:
            return Repo.from_json(cursor, response.json())
        else: return None

    def contributors(self, cursor):
        if self.is_searched:
            db_response = cursor.execute(
                    'SELECT UserId FROM GithubContributions WHERE RepoId = ?', 
                    (self.repo_id,))

            result = []
            for row in db_response:
                values = cursor.execute(
                    'SELECT * FROM GithubUsers WHERE Id = ?',
                    row).fetchone()
                result.append(User(cursor, *values))
            return result

        else:
            items = paginate_api(
                    'repos/' + self.owner_login + 
                    '/' + self.name + '/contributors')

            result = []
            for data in items:
                user = User.from_json(data, cursor)
                cursor.execute('INSERT OR REPLACE INTO GithubContributions VALUES(?,?)',
                        (user.user_id, self.repo_id))
                result.append(user)

            self.is_searched = 1
            self.store(cursor)
            cursor.commit()
            return result

    def store(self, cursor):
        values = (self.repo_id, self.owner_id, self.owner_login, self.name, 
                self.language, self.is_fork, self.homepage, 
                self.is_searched)
        cursor.execute('REPLACE INTO GithubRepos VALUES(?,?,?,?,?,?,?,?)',
                values)
