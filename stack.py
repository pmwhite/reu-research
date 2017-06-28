import xml.etree.ElementTree as ET
import itertools
import sqlite3
import time
import re

# An iterator of all the children of a given xml file. The file is
# assumed to be of depth 1, since the StackExchange data dump files also
# have depth.
def xml_children(filename):
    for event, child in ET.iterparse(filename):
        if event == 'end' and child.tag == 'row':
            yield child.attrib
        child.clear()


# Deletes all tag data from the database and reloads it from the xml file.
def reload_tags(cursor):

    print('Deleting tag data')
    cursor.execute('DELETE FROM StackTags')

    # Get the iterator of value tuples to pass to the SQL engine.
    children = xml_children('data/Tags.xml')
    values = ((child['Id'], child['TagName'], child['Count']) 
            for child in children)

    print('Loading tag data')
    cursor.executemany('INSERT INTO StackTags VALUES(?, ?, ?)', values)


# Deletes all user data from the database and reloads it from the xml file.
def reload_users(cursor):

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
            user_id = child.get('Id', None)
            if user_id == None: continue
            display_name = child['DisplayName']
            reputation = child['Reputation']
            website_url = child.get('WebsiteUrl', None)
            if website_url == '': website_url = None
            age = child.get('Age', None)
            location = child.get('Location', None)
            if location == '': location = None
            yield (user_id, display_name, reputation, 
                    website_url, age, location)
            count = count + 1
            if count % 10000 == 0: print(count, 'lines processed')
    print('Loading user data')

    # Ignore insertion if the account id is a duplicate.
    cursor.executemany(
            'INSERT OR IGNORE INTO StackUsers VALUES(?, ?, ?, ?, ?, ?)', 
            values())

def reload_comments(cursor):
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

def reload_posts(cursor):
    print('Deleting post data')
    cursor.execute('DELETE FROM StackPosts')

    children = xml_children('data/Posts.xml')

    tag_data = dict(
            cursor.execute('SELECT TagName, Id FROM StackTags').fetchmany(100000))

    print('Loading post data')
    count = 0
    for child in children:
        post_id = child['Id']
        post_type = child['PostTypeId']
        score = child['Score']
        owner_user_id = child.get('OwnerUserId', None)
        accepted_answer_id = child.get('AcceptedAnswerId', None)
        parent_id = child.get('ParentId', None)
        cursor.execute('INSERT INTO StackPosts VALUES(?,?,?,?,?,?)',
                (post_id, post_type, score, owner_user_id, 
                    accepted_answer_id, parent_id))

        tags_str = child.get('Tags', None)
        if tags_str:
            tags = re.findall('<(.*?)>', tags_str)
            for tag in tags:
                tag_id = tag_data[tag]
                cursor.execute('INSERT INTO StackTagAssignments VALUES(?,?)',
                    (post_id, tag_id))

        count = count + 1
        if count % 10000 == 0: print(count / 1000000.0)

class User:

    def __init__(self, user_id, display_name, reputation, website_url, age, location):
        self.user_id = user_id
        self.display_name = display_name
        self.reputation = reputation
        self.website_url = website_url
        self.age = age
        self.location = location

    def __repr__(self):
        return 'StackUsers({0}, {1}, {2}, {3}, {4}, {5})'.format(
                self.user_id, self.display_name, self.reputation,
                self.website_url, self.age, self.location)

    def __str__(self):
        return 'StackUser({0})'.format(self.display_name)

    def __hash__(self):
        return self.user_id
    
    def __eq__(self, other):
        return self.user_id == other.user_id

    def get_json(self):
        props = [('id', self.user_id),
                 ('displayName', self.display_name),
                 ('reputation', self.reputation),
                 ('websiteUrl', self.website_url),
                 ('age', self.age),
                 ('location', self.location)]
        return dict((k, v) for k, v in props if v is not None)

    def fetch_id(user_id, cursor):
        values = cursor.execute(
                'SELECT * FROM StackUsers WHERE Id = ?',
                (user_id,)).fetchone()
        print(values)
        return User(*values)

    def fetch_display_name(display_name, cursor):
        users = cursor.execute(
                'SELECT * FROM StackUsers WHERE DisplayName = ?',
                (display_name,)).fetchall()
        return (User(*values) for values in users)

    def answerers(self, cursor):
        answerers = cursor.execute('''
            SELECT answerers.* FROM StackUsers su
            JOIN StackPosts sp ON su.Id = sp.OwnerUserId
            JOIN StackPosts answers ON answers.Id = sp.AcceptedAnswerId
            JOIN StackUsers answerers ON answerers.Id = answers.OwnerUserId
            WHERE su.Id = ?''', (self.user_id,)).fetchall()

        for values in answerers:
            yield User(*values)

    def questioners(self, cursor):
        questioners = cursor.execute('''
            SELECT questioners.* FROM StackUsers su
            JOIN StackPosts sp ON su.Id = sp.OwnerUserId
            JOIN StackPosts questions ON questions.Id = sp.ParentId
            JOIN StackUsers questioners ON questioners.Id = questions.OwnerUserId
            WHERE su.Id = ?''', (self.user_id,)).fetchall()
        
        for values in questioners:
            yield User(*values)
