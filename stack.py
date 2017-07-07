import xml.etree.ElementTree as ET
import itertools
import sqlite3
import time
import re
from misc import clean_str_key
from collections import namedtuple

def xml_children(filename):
    for event, child in ET.iterparse(filename):
        if event == 'end' and child.tag == 'row':
            yield child.attrib
        child.clear()

User = namedtuple('User', 'id display_name reputation website_url age location')
Tag = namedtuple('Tag', 'id name count')
Comment = namedtuple('Comment', 'id post_id score user_id')
Post = namedtuple('Post', 'id post_type_id score owner_user_id accepted_answer_id tags')

def user_from_xml(xml):
    if 'Id' in xml:
        return User(
                id=xml['Id'],
                display_name=xml['DisplayName'],
                reputation=xml['Reputation'],
                website_url=clean_str_key(xml, 'WebsiteUrl'),
                age=xml.get('Age', None),
                location=clean_str_key(xml, 'Location'))

def store_user(user, conn):
    conn.execute('INSERT INTO StackUsers VALUES(?,?,?,?,?,?)', user)

def tag_from_xml(xml):
    return Tag(id=xml['Id'], name=xml['TagName'], count=xml['Count'])

def store_tag(tag, conn):
    conn.execute('INSERT INTO StackTags VALUES(?,?,?)', tag)

def comment_from_xml(xml):
    if 'UserId' in xml:
        return Comment(
                id=xml['Id'],
                post_id=xml['PostId'],
                score=xml['Score'],
                user_id=xml['UserId'])

def store_comment(comment, conn):
    conn.execute('INSERT INTO StackComments VALUES(?,?,?,?)', comment)

def post_from_xml(xml, tag_data):
    tags_str = child.get('Tags', None)
    tags=[]
    if tags_str:
        tag_names = re.findall('<(.*?)>', tags_str)
        tags = {tag_data[name] for name in tag_names}
    return Post(
            id=xml['Id'],
            post_type_id=xml['PostTypeId'],
            score=xml['Score'],
            owner_user_id=xml['OwnerUserId'],
            accepted_answer_id=xml['AcceptedAnswerId'],
            tag_ids=tags)

def store_post(post, conn):
    conn.execute('INSERT INTO StackPosts VALUES(?,?,?,?,?,?)', post[:-1])
    for tag in post.tags:
        conn.execute('INSERT INTO StackTagAssignments VALUES(?,?)',
                    (post.id, tag.id))

def reload_tags(conn):
    print('Deleting tag data')
    conn.execute('DELETE FROM StackTags')
    for child in xml_children('data/Tags.xml'):
        store_tag(tag_from_xml(child), conn)
    print('Loading tag data')

def reload_users(conn):
    print('Deleting user data')
    conn.execute('DELETE FROM StackUsers')
    print('Loading user data')
    for count, child in enumerate(xml_children('data/Users.xml')):
        user = user_from_xml(child)
        if user is not None:
            store_user(user, conn)
        if count % 10000 == 0: 
            conn.commit()
            print(count, 'lines processed')

def reload_comments(conn):
    print('Deleting comment data')
    conn.execute('DELETE FROM StackComments')
    print('Loading comment data')
    for count, child in enumerate(xml_children('data/Comments.xml')):
        comment = comment_from_xml(child)
        if comment is not None:
            store_comment(comment, conn)
        if count % 100000 == 0: 
            conn.commit()
            print(count / 1000000.0)

def reload_posts(conn):
    print('Deleting post data')
    conn.execute('DELETE FROM StackPosts')
    children = xml_children('data/Posts.xml')
    tag_rows = conn.execute(
        'SELECT * FROM StackTags').fetchall()
    tag_data = {name: Tag(id=id, name=name, count=count) 
            for (id, name, count) in tag_rows}
    print('Loading post data')
    for count, child in enumerate(children):
        post = post_from_xml(child, tag_data)
        store_post(post, conn)
        if count % 10000 == 0: 
            conn.commit()
            print(count / 1000000.0)

def user_to_json(user):
    return {'id': user.id,
            'displayName': user.display_name,
            'reputation': user.reputation,
            'websiteUrl': user.websiteUrl,
            'age': user.age,
            'location': user.location}

def fetch_id(user_id, conn):
    row = conn.execute(
            'SELECT * FROM StackUsers WHERE Id = ?',
            (user_id,)).fetchone()
    return User(*row)

def user_answerers(user, conn):
    rows = conn.execute('''
        SELECT answerers.* FROM StackUsers su
        JOIN StackPosts sp ON su.Id = sp.OwnerUserId
        JOIN StackPosts answers ON answers.Id = sp.AcceptedAnswerId
        JOIN StackUsers answerers ON answerers.Id = answers.OwnerUserId
        WHERE su.Id = ?''', (user.id,)).fetchall()
    return [User(*row) for row in rows]

def user_questioners(user, conn):
    rows = conn.execute('''
        SELECT questioners.* FROM StackUsers su
        JOIN StackPosts sp ON su.Id = sp.OwnerUserId
        JOIN StackPosts questions ON questions.Id = sp.ParentId
        JOIN StackUsers questioners ON questioners.Id = questions.OwnerUserId
        WHERE su.Id = ?''', (user.id,)).fetchall()
    return [User(*row) for row in rows]
