import requests
import time
import datetime
import sqlite3
import itertools
import keys
import re
import misc
from misc import clean_str_key
from datetime import datetime
from collections import namedtuple

def graphql_request(query):
    def make_request():
        return requests.post(
                url='https://api.github.com/graphql',
                params={'access_token': keys.GITHUB_KEY},
                json={'query': query})
    def extract_rate_info(response):
        info = response.json()['data']['rateLimit']
        reset_time = datetime.strptime(
                info['resetAt'], 
                '%Y-%m-%dT%H:%M:%SZ').timestamp()
        requests_left = info['remaining']
        return (reset_time, requests_left)
    return misc.rated_request(make_request, extract_rate_info)

def paginate_gql_connection(baseQuery, nodes_path):
    def make_request(cursor):
        cursor_str = ''
        if cursor is not None:
            cursor_str = 'after: "%s"' % cursor
        return graphql_request(baseQuery % cursor_str)
    def extract_cursor(response):
        data = response.json()['data']
        for path_item in nodes_path:
            data = data[path_item]
        page_info = data['pageInfo']
        if page_info['hasNextPage']:
            return page_info['endCursor']
    def extract_items(response):
        data = response.json()['data']
        for path_item in nodes_path:
            data = data[path_item]
        for node in data['nodes']:
            yield node
    return misc.paginate_api(make_request, extract_cursor, extract_items)

User = namedtuple('User', 'id login location email name website_url company')
Repo = namedtuple('Repo', 'id owner_id owner_login name language homepage is_fork')

# Dict -> User
def user_from_json(data):
    return User(
            id=data['id'],
            login=data['login'],
            location=clean_str_key(data, 'location'),
            email=clean_str_key(data, 'email'),
            name=clean_str_key(data, 'name'),
            website_url=clean_str_key(data, 'websiteUrl'),
            company=clean_str_key(data, 'company'))

# User -> Dict
def user_to_json(user):
    return {'id': user.id,
            'login': user.login,
            'location': user.location,
            'email': user.email,
            'websiteUrl': user.website_url,
            'company': user.company}

# Dict -> Repo
def repo_from_json(data):
    if data['primaryLanguage'] is not None:
        language = data['primaryLanguage']['name']
    else:
        language = None
    return Repo(
            id=data['id'],
            owner_id=data['owner']['id'],
            owner_login=data['owner']['login'],
            name=data['name'],
            language=language,
            is_fork=data['isFork'],
            homepage=clean_str_key(data, 'homepageUrl'))

# Repo -> Dict
def repo_to_json(repo):
    return {'id': repo.id,
            'ownerId': repo.owner_id,
            'ownerLogin': repo.owner_login,
            'name': repo.name,
            'language': repo.language,
            'isFork': repo.is_fork,
            'homepage': repo.homepageUrl}

# String -> String
def clean_login(login): 
    return '_' + ''.join(['%.5d' % ord(c) for c in login])

# String list -> Map<String, User option>
def user_fetch_logins_api(logins):
    user_snippet = '''
        %s:repositoryOwner(login: "%s") {
            login 
            id 
            ... on User {
                location email name websiteUrl company 
            }
        }'''
    rate_snippet = 'rateLimit { remaining resetAt cost }'
    result = {}
    for login_group in misc.grouper(logins, 100):
        users_snippet = '\n'.join(
                [user_snippet % (clean_login(login), login) for login in login_group])
        query_str = 'query {\n%s\n%s}' % (users_snippet, rate_snippet)
        response = graphql_request(query_str)
        data = response.json()['data']
        for login in login_group:
            json = data[clean_login(login)]
            if json is not None:
                result[login] = user_from_json(json)
            else:
                result[login] = None
    return result

# String -> DB -> User option
def user_fetch_login_db(login, conn):
    db_response = conn.execute(
            'SELECT * FROM GithubUsers WHERE Login = ?', 
            (login,)).fetchone()
    if db_response:
        return User(*db_response)
    else:
        return None

# String list -> DB -> Map<String, User option>
def user_fetch_logins_db(logins, conn):
    return {login: user_fetch_login_db(login, conn) for login in logins}

# String list -> DB -> Map<String, User option>
def user_fetch_logins(logins, conn):
    result = user_fetch_logins_db(logins, conn)
    api = user_fetch_logins_api([login for login, user in result.items() if user is None])
    for login, user in api.items():
        if user is not None:
            store_user(user, conn)
            result[login] = user
    return result

# String -> DB -> User option
def user_fetch_login(login, conn):
    return user_fetch_logins([login], conn)[login]

def user_repos_api(user):
    baseQuery = '''
        query { 
            rateLimit { remaining resetAt cost }
            repositoryOwner(login: "''' + user.login + '''") {
                repositories(first: 100, %s) {
                    pageInfo { hasNextPage endCursor }
                    nodes {
                        id
                        owner { id login }
                        name
                        primaryLanguage { name }
                        homepageUrl
                        isFork
                    }
                }
            }
        }'''
    for item in paginate_gql_connection(baseQuery, ['repositoryOwner', 'repositories']):
        repo = repo_from_json(item)
        if repo.owner_id == user.id:
            yield repo

def user_repos_db(user, conn):
    db_response = conn.execute(
        'SELECT * FROM GithubRepos WHERE OwnerId = ?',
        (user.id,)).fetchall()
    for values in db_response:
        yield Repo(*values)

def store_user(user, conn):
    values = (user.id, user.login, user.location, 
            user.email, user.name, user.website_url, user.company)
    conn.execute(
            'INSERT OR IGNORE INTO GithubUsers VALUES(?,?,?,?,?,?,?)',
            values)

def store_repo(repo, conn):
    values = (repo.id, repo.owner_id, repo.owner_login, repo.name, 
            repo.language, repo.is_fork, repo.homepage)
    conn.execute(
            'INSERT OR IGNORE INTO GithubRepos VALUES(?,?,?,?,?,?,?)',
            values)

def store_repo_contributor(repo, contributor, conn):
    store_user(contributor, conn)
    conn.execute('INSERT INTO GithubContributions VALUES(?,?)',
            (contributor.id, repo.id))

user_repos = misc.CachedSearch(
        db_fetch=user_repos_db,
        api_fetch=user_repos_api,
        store=lambda _, repo, conn: store_repo(repo, conn),
        search_type='github:repository')

def repo_contributors_db(repo, conn):
    id_rows = conn.execute(
            'SELECT UserId FROM GithubContributions WHERE RepoId = ?', 
            (repo.id,)).fetchall()
    for row in id_rows:
        values = conn.execute(
            'SELECT * FROM GithubUsers WHERE Id = ?',
            row).fetchone()
        yield User(*values)

def repo_contributors_api(repo):
    baseQuery = '''
        query {
            rateLimit { remaining resetAt cost }
            repository(name: \"''' + repo.name + '\", owner: \"' + repo.owner_login + '''\") {
                mentionableUsers(first:100, %s) {
                    pageInfo { hasNextPage endCursor }
                    nodes {
                        id login location email name websiteUrl company
                    }
                }
            }
        }'''
    for item in paginate_gql_connection(baseQuery, ['repository', 'mentionableUsers']):
        yield user_from_json(item)

repo_contributors = misc.CachedSearch(
        db_fetch=repo_contributors_db,
        api_fetch=repo_contributors_api,
        store=store_repo_contributor,
        search_type='github:contributor')

def user_contributed_repos_db(user, conn):
    id_rows = conn.execute(
            'SELECT RepoId FROM GithubContributions WHERE UserId = ?', 
            (user.id,)).fetchall()
    for row in id_rows:
        values = conn.execute(
            'SELECT * FROM GithubRepos WHERE Id = ?',
            row).fetchone()
        yield Repo(*values)

def user_contributed_repos_api(user):
    isUserQuery = '''
        query {
            repositoryOwner(login: "''' + user.login + '''") {
                __typename
            }
            rateLimit { remaining resetAt }
        }'''
    if graphql_request(isUserQuery).json()['data']['repositoryOwner']['__typename'] == 'User':
        baseQuery = '''
            query { 
                rateLimit { remaining resetAt cost }
                user(login: "''' + user.login + '''") {
                    contributedRepositories(first: 100, %s) {
                        pageInfo { hasNextPage endCursor }
                        nodes {
                            id
                            owner { id login }
                            name
                            primaryLanguage { name }
                            homepageUrl
                            isFork
                        }
                    }
                }
            }'''
        for item in paginate_gql_connection(
                baseQuery, ['user', 'contributedRepositories']):
            yield repo_from_json(item)

def store_user_contributed_repo(user, contributed_repo, conn):
    store_repo(contributed_repo, conn)
    conn.execute('INSERT INTO GithubContributions VALUES(?,?)',
            (user.id, contributed_repo.id))

def user_contributed_repos(user, conn):
    return misc.cached_search(
            entity=user,
            db_search=user_contributed_repos_db,
            global_search=user_contributed_repos_api,
            store=store_user_contributed_repo,
            search_type='github:contributed_repository',
            conn=conn)

def user_parents(user, conn):
    for repo in github.user_repos(user, conn):
        if not repo.is_fork:
            for contributor in github.repo_contributors(repo, conn):
                yield contributor

def user_children(user, conn):
    for repo in github.user_contributed_repos(user, conn):
        yield github.user_fetch_login(repo.owner_login, conn)
