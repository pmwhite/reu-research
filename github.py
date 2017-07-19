from network import Walk
from visualization import NodeVisualizer
from misc import clean_str_key
from datetime import datetime
from collections import namedtuple
import keys
import misc
import rest

def graphql_request(query, conn):
    def make_request():
        return rest.cached_post(
                url='https://api.github.com/graphql',
                params={'access_token': keys.GITHUB_KEY},
                json={'query': query},
                conn=conn)
    def extract_rate_info(response):
        info = response.json()['data']['rateLimit']
        reset_time = datetime.strptime(
                info['resetAt'], 
                '%Y-%m-%dT%H:%M:%SZ').timestamp()
        requests_left = info['remaining']
        return (reset_time, requests_left)
    return misc.rated_request(make_request, extract_rate_info)

def paginate_gql_connection(baseQuery, nodes_path, conn):
    def make_request(cursor):
        cursor_str = ''
        if cursor is not None:
            cursor_str = 'after: "%s"' % cursor
        return graphql_request(baseQuery % cursor_str, conn)
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
        response = graphql_request(query_str, conn)
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
    for item in paginate_gql_connection(baseQuery, ['repositoryOwner', 'repositories'], conn):
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
    for item in paginate_gql_connection(baseQuery, ['repository', 'mentionableUsers'], conn):
        yield user_from_json(item)

def user_contributed_repos(user, conn):
    isUserQuery = '''
        query {
            repositoryOwner(login: "''' + user.login + '''") {
                __typename
            }
            rateLimit { remaining resetAt }
        }'''
    if graphql_request(isUserQuery, conn).json()['data']['repositoryOwner']['__typename'] == 'User':
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
                paginate_gql_connection(baseQuery, ['user', 'contributedRepositories'], conn))
    else:
        return []

user_attribute_schema = {
        'id': 'string', 
        'login': 'string', 
        'location': 'string',
        'email': 'string',
        'name': 'string',
        'website_url': 'string',
        'company': 'string'}

def user_serialize(user):
    return user._asdict()

def user_label(user):
    return user.login

user_visualizer = NodeVisualizer(
        schema=user_attribute_schema,
        serialize=user_serialize,
        label=user_label)

def user_out_gen(user, conn):
    for repo in user_contributed_repos(user, conn):
        yield user_fetch_login(repo.owner_login, conn)

def user_in_gen(user, conn):
    for repo in user_repos(user, conn):
        if not repo.is_fork:
            for contributor in repo_contributors(repo, conn):
                yield contributor

def user_select_leaves(leaves): 
    for leaf in leaves:
        if leaf.login == 'Try-Git':
            continue
        else: 
            yield leaf

user_walk = Walk(
        out_gen=user_out_gen,
        in_gen=user_in_gen,
        select_leaves=user_select_leaves)
