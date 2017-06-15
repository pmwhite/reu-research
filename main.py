import sqlite3
import github
import twitter
import keys
import stack

with sqlite3.connect('data/data.db') as conn:
    cursor = conn.cursor()
