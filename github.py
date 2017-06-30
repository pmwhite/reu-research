import requests
import time
import sqlite3
import itertools
import keys
import re
from misc import clean_str

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

def paginate_api(path, start_params={}):
    response = request_api(path, params=start_params)
    def next_page_link():
        link = response.headers.get('Link', None)
        if link == None:
            return None
        else: return re.findall('<(.*?)>', link)[0].strip('<').strip('>')
    next_page_url = next_page_link()
    first_link = next_page_url
    while response.status_code == 200:
        for item in response.json():
            yield item
        if not next_page_url: break
        response = rated_request(next_page_url)
        next_page_url = next_page_link()
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

class User:
    def __init__(self, user_id, login, 
            location, email, name, 
            blog, company, is_searched):
        self.user_id = user_id
        self.login = login
        self.location = clean_str(location)
        self.email = clean_str(email)
        self.name = clean_str(name)
        self.blog = clean_str(blog)
        self.company = clean_str(company)
        self.is_searched = is_searched

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

    def from_json(data, conn):
        user_id = data['id']
        is_searched_row = conn.execute(
                'SELECT IsSearched FROM GithubUsers WHERE Id = ?',
                (user_id,)).fetchone()
        is_searched = 0
        if is_searched_row is not None:
            is_searched = is_searched_row[0]
        user = User(
                user_id=user_id,
                login=data['login'],
                location=data.get('location', None),
                email=data.get('email', None),
                name=data.get('name', None),
                blog=data.get('blog', None),
                company=data.get('company', None),
                is_searched=is_searched)
        user.ensure_storage(conn)
        return user

    def repos(self, conn):
        if self.is_searched != 0:
            db_response = conn.execute(
                'SELECT * FROM GithubRepos WHERE OwnerId = ?',
                (self.user_id,)).fetchall()
            for values in db_response:
                yield Repo(*values)
        else: 
            for data in paginate_api('users/' + self.login + '/repos', 
                    start_params={'per_page':100}):
                yield Repo.from_json(data, conn)
            self.is_searched = 1
            conn.execute(
                    'UPDATE GithubUsers SET IsSearched = 1 WHERE Id = ?',
                    (self.user_id,))
            conn.commit()

    def ensure_storage(self, conn):
        values = (self.user_id, self.login, self.location, 
                self.email, self.name, self.blog, self.company, 
                self.is_searched)
        conn.execute(
                'INSERT OR IGNORE INTO GithubUsers VALUES(?,?,?,?,?,?,?,?)',
                values)

    def refill(self, conn):
        user = User.api_fetch_login(self.login)
        update_values = (user.location, user.email, user.name, 
                user.blog, user.company, self.user_id)
        conn.execute('''
                UPDATE GithubUsers SET Location = ?, Email = ?, Name = ?, Blog = ?, Company = ?
                WHERE Id = ?''',
                update_values)

    def api_fetch_login(login, conn):
        response = request_api('users/' + login)
        if response.status_code == 200: 
            return User.from_json(response.json(), conn)

    def db_fetch_login(login, conn):
        db_response = conn.execute(
                'SELECT * FROM GithubUsers WHERE Login = ?', 
                (login,)).fetchone()
        if db_response: 
            return User(*db_response)

    def gen_fetch_login(login, conn):
        db = User.db_fetch_login(login, conn)
        if db is not None:
            return db
        else:
            return User.api_fetch_login(login, conn)

    def db_fetch_id(user_id, conn):
        db_response = conn.execute(
                'SELECT * FROM GithubUsers WHERE Id = ?', 
                (user_id,)).fetchone()
        if db_response: 
            return User(*db_response)

    def fetch_after(since_id, conn):
        for item in paginate_api('users', start_params={'since': since_id}):
            yield User.from_json(item, conn)

class Repo:
    def __init__(self, repo_id, owner_id, owner_login, name, 
            language, is_fork, homepage, is_searched):
        self.repo_id = repo_id
        self.owner_login = owner_login
        self.name = name
        self.owner_id = owner_id
        self.language = language
        self.homepage = clean_str(homepage)
        self.is_fork = is_fork
        self.is_searched = is_searched

    def __str__(self):
        return 'Repo({0}/{1}, {2})'.format(
                self.owner_login, self.name, self.language)

    def from_json(data, conn):
        repo = Repo(
                repo_id=data['id'],
                owner_id=data['owner']['id'], 
                owner_login=data['owner']['login'], 
                name=data['name'],
                language=data['language'], 
                is_fork=data['fork'], 
                homepage=data['homepage'],
                is_searched=0)
        repo.ensure_storage(conn)
        return repo

    def contributors(self, conn):
        if self.is_searched:
            id_rows = conn.execute(
                    'SELECT UserId FROM GithubContributions WHERE RepoId = ?', 
                    (self.repo_id,)).fetchall()
            for row in id_rows:
                values = conn.execute(
                    'SELECT * FROM GithubUsers WHERE Id = ?',
                    row).fetchone()
                yield User(*values)
        else:
            items = paginate_api(
                    'repos/' + self.owner_login + 
                    '/' + self.name + 
                    '/contributors')
            for data in items:
                user = User.from_json(data, conn)
                conn.execute('INSERT INTO GithubContributions VALUES(?,?)',
                        (user.user_id, self.repo_id))
                yield user
            self.is_searched = 1
            conn.execute(
                    'UPDATE GithubRepos SET IsSearched = 1 WHERE Id = ?',
                    (self.repo_id,))
            conn.commit()

    def ensure_storage(self, conn):
        values = (self.repo_id, self.owner_id, self.owner_login, self.name, 
                self.language, self.is_fork, self.homepage, self.is_searched)
        conn.execute(
                'INSERT OR IGNORE INTO GithubRepos VALUES(?,?,?,?,?,?,?,?)',
                values)
