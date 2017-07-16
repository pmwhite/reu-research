import requests
import time
import datetime
import sqlite3
import itertools
import keys
import re
import misc
import rest
from misc import clean_str_key
from datetime import datetime
from collections import namedtuple

def graphql_request(query):
    def make_request():
        return rest.cached_post(
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

# String -> String
def clean_login(login): 
    return '_' + ''.join(['%.5d' % ord(c) for c in login])

# String list -> Map<String, User option>
def user_fetch_logins(logins, conn):
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
def user_fetch_login(login, conn):
    return user_fetch_logins([login], conn)[login]

def user_repos(user, conn):
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

def repo_contributors(repo, conn):
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

def user_contributed_repos(user, conn):
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
        return (repo_from_json(item) for item in 
                paginate_gql_connection(baseQuery, ['user', 'contributedRepositories']))
    else:
        return []
