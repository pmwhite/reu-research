import stack
import sqlite3
import common
import deanon
import os
import graph

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

def populate_network(username, stack_id, depth, cursor):
    populate_github_network(username)
    populate_twitter_network(username)
    populate_stack_network(stack_id)

def run_stuff(conn):
    while True:
        try:
            for s_user, t_user, g_user in common.active_matches(20, 20, 8, conn):
                print('=' * 80, t_user.screen_name, '=' * 80)
                if not os.path.isfile('outputs/twitter_' + t_user.screen_name + '.gexf'):
                    (t_net, g_net, tg_seeds) = deanon.queue_seed_tg(t_user, g_user, 20, conn)
                    mashed = graph.mash(t_net, g_net, tg_seeds, deanon.mash_tg)
                    graph.to_gefx(
                            mashed, 
                            deanon.tg_attribute_schema, 
                            deanon.serialize_tg, 
                            deanon.label_tg).write('outputs/mashed_' + t_user.screen_name + '.gexf')
                    graph.write_twitter(t_net, 'outputs/twitter_' + t_user.screen_name + '.gexf')
                    graph.write_github(g_net, 'outputs/github_' + t_user.screen_name + '.gexf')
                conn.commit()
        except Exception as e:
           print(e)
