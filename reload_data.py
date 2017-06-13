import xml.etree.ElementTree as ET
from collections import defaultdict
import sqlite3

def xml_children(filename):
    for event, child in ET.iterparse(filename):
        if event == 'end' and child.tag == 'row':
            yield child.attrib
        child.clear()

def reload_stack_tags(cursor):
    print('Deleting tag data')
    cursor.execute('DELETE FROM StackTags')
    children = xml_children('Tags.xml')
    values = ((child['Id'], child['TagName'], child['Count']) for child in children)
    print('Loading tag data')
    cursor.executemany('INSERT INTO StackTags VALUES(?, ?, ?)', values)

def reload_stack_users(cursor):
    print('Deleting user data')
    cursor.execute('DELETE FROM StackUsers')
    children = xml_children('Users.xml')
    def values():
        count = 0
        for child in children:
            account_id = child.get('AccountId', None)
            if account_id == None: continue
            display_name = child['DisplayName']
            reputation = child['Reputation']
            website_url = child.get('WebsiteUrl', None)
            if website_url == '': website_url = None
            age = child.get('Age', None)
            location = child.get('Location', None)
            if location == '': location = None
            yield (account_id, display_name, reputation, website_url, age, location)
            count = count + 1
            if count % 10000 == 0: print(count, 'lines processed')
    print('Loading user data')
    cursor.executemany(
            'INSERT OR IGNORE INTO StackUsers VALUES(?, ?, ?, ?, ?, ?)', 
            values())
