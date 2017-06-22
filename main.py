import sqlite3
import stack

with sqlite3.connect('data/data.db') as conn:
    cursor = conn.cursor()
    # stack.reload_stack_users(cursor)
