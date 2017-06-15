import xml.etree.ElementTree as ET
import itertools
import sqlite3

# An iterator of all the children of a given xml file. The file is
# assumed to be of depth 1, since the StackExchange data dump files also
# have depth.
def xml_children(filename):
    for event, child in ET.iterparse(filename):
        if event == 'end' and child.tag == 'row':
            yield child.attrib
        child.clear()


# Deletes all tag data from the database and reloads it from the xml file.
def reload_stack_tags(cursor):

    print('Deleting tag data')
    cursor.execute('DELETE FROM StackTags')

    # Get the iterator of value tuples to pass to the SQL engine.
    children = xml_children('data/Tags.xml')
    values = ((child['Id'], child['TagName'], child['Count']) 
            for child in children)

    print('Loading tag data')
    cursor.executemany('INSERT INTO StackTags VALUES(?, ?, ?)', values)


# Deletes all user data from the database and reloads it from the xml file.
def reload_stack_users(cursor):

    print('Deleting user data')
    cursor.execute('DELETE FROM StackUsers')

    # Get the tuple generator to feed into the SQL engine.
    children = xml_children('data/Users.xml')
    def values():
        count = 0
        for child in children:
            # Grab various attributes; make sure the account id is valid, and
            # replace empty strings with NULL. Note that 'None' in python is
            # NULL in SQL.
            account_id = child.get('AccountId', None)
            if account_id == None: continue
            display_name = child['DisplayName']
            reputation = child['Reputation']
            website_url = child.get('WebsiteUrl', None)
            if website_url == '': website_url = None
            age = child.get('Age', None)
            location = child.get('Location', None)
            if location == '': location = None
            yield (account_id, display_name, reputation, 
                    website_url, age, location)
            count = count + 1
            if count % 10000 == 0: print(count, 'lines processed')
    print('Loading user data')

    # Ignore insertion if the account id is a duplicate.
    cursor.executemany(
            'INSERT OR IGNORE INTO StackUsers VALUES(?, ?, ?, ?, ?, ?)', 
            values())

def reload_stack_comments(cursor):
    print('Deleting comment data')
    cursor.execute('DELETE FROM StackComments')

    children = xml_children('data/Comments.xml')

    print('Loading comment data')
    def values():
        count = 0
        for child in children:
            if child.get('UserId', None) == None:
                continue
            yield ((child['Id'], child['PostId'], child['Score'], child['UserId']))
            count += 1
            if count % 100000 == 0: print(count / 1000000.0)

    cursor.executemany('INSERT INTO StackComments VALUES(?,?,?,?)', values())

def reload_stack_posts(cursor):
    print('Deleting post data')
    cursor.execute('DELETE FROM StackPosts')

    children = xml_children('data/Posts.xml')

    print('Loading post data')
    for child in children:
        post_id = child['Id']
        post_type = child['PostTypeId']

        if post_type == 1:

