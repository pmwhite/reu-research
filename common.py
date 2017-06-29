import github
import stack
import twitter

def find_common_users(conn):
    last_github_id = conn.execute(
            'SELECT Value FROM Dict WHERE Key = "next github id"')
    previous_users = conn.execute('''
            SELECT gu.Id, tu.Id, su.Id FROM GithubUsers gu
            JOIN TwitterUsers tu ON gu.Login = tu.ScreenName
            JOIN StackUsers su ON gu.Login = su.ScreenName
            ''')
    for (github_id, twitter_id, stack_id) in previous_users:
        github_user = github.User.db_fetch_id(github_id conn)
        twitter_user = twitter.User.db_fetch_id(twitter_id, conn)
        stack_user = stack.User.fetch_id(stack_id, conn)
        yield (github_user, twitter_user, stack_user)
    for user in github.User.fetch_after(last_github_id):

