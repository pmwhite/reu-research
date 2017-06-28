import stack
import sqlite3

def reload_stack_data(datafile, posts=True, comments=True, users=True, tags=True):
    with sqlite3.connect(datafile) as conn:
        cursor = conn.cursor()
        if posts: 
            print('Reloading posts')
            stack.reload_posts(cursor)
            conn.commit()

        if comments: 
            print('Reloading comments')
            stack.reload_comments(cursor)
            conn.commit()

        if users: 
            print('Reloading users')
            stack.reload_users(cursor)
            conn.commit()

        if tags: 
            print('Reloading tags')
            stack.reload_tags(cursor)
            conn.commit()

def pull_github_connections(login, cursor):
    user = pull_github_user(login)

    


def pull_github_twitter_users(cursor):
    for github_group in grouper(github_users(), 95):
        logins = (user['login'] for user in github_group)
        twitter_users = check_twitter_users(logins)
        for user in github_group:
            store_github_user(user, cursor)

        for user in twitter_users:
            store_twitter_user(user, cursor)


def populate_network(username, stack_id, depth, cursor):
    populate_github_network(username)
    populate_twitter_network(username)
    populate_stack_network(stack_id)
