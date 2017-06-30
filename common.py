import github
import stack
import twitter
import sqlite3
import itertools
from misc import grouper

def find_common_users(conn):
    (last_github_id,) = conn.execute(
            'SELECT Value FROM Dict WHERE Key = "next github id"').fetchone()
    print(last_github_id)
    prev_github_twitter_rows = conn.execute('''
            SELECT gu.Id, tu.Id, gu.Login FROM GithubUsers gu
            JOIN TwitterUsers tu ON gu.Login = tu.ScreenName
            WHERE gu.Id < ?
            ''', (last_github_id,))
    for (github_id, twitter_id, common_name) in prev_github_twitter_rows:
        github_user = github.User.db_fetch_id(github_id, conn)
        twitter_user = twitter.User.db_fetch_id(twitter_id, conn)
        stack_users = stack.User.fetch_display_name(common_name, conn)
        yield (github_user, twitter_user, stack_users)
    next_github_users = github.User.fetch_after(last_github_id, conn)
    for group in grouper(next_github_users, 100):
        github_group = list(group)
        github_logins = [user.login for user in github_group]
        twitter_parallels = list(twitter.User.fetch_screen_names(github_logins, conn))
        for github_user in github_group:
            for twitter_user in twitter_parallels:
                if github_user.login == twitter_user.screen_name:
                    stack_users = stack.User.fetch_display_name(github_user.login, conn)
                    yield (github_user, twitter_user, stack_users)
        conn.execute(
                'UPDATE Dict SET Value = ? WHERE Key = "next github id"',
                (github_group[-1].user_id,))
        conn.commit()
