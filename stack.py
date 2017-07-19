import xml.etree.ElementTree as ET
import re
from network import Walk
from visualization import NodeVisualizer
from misc import clean_str_key
from collections import namedtuple
from datetime import datetime

def xml_children(filename):
    for event, child in ET.iterparse(filename):
        if event == 'end' and child.tag == 'row':
            yield child.attrib
        child.clear()

User = namedtuple('User', 'id display_name reputation website_url age location')
Tag = namedtuple('Tag', 'id name count')
Comment = namedtuple('Comment', 'id post_id score user_id created_at')
Post = namedtuple('Post', 'id score owner_user_id parent_id created_at tags')

def parse_date(date_str):
    return datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S.%f')

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
                user_id=xml['UserId'],
                created_at=parse_date(xml['CreationDate']))

def comment_from_db(row):
    (c_id, post_id, score, user_id, created_at_stamp) = row
    return Comment(
            id=c_id,
            post_id=post_id,
            score=score,
            user_id=user_id,
            created_at=datetime.utcfromtimestamp(created_at_stamp))

def store_comment(c, conn):
    vs = (c.id, c.post_id, c.score, c.user_id, c.created_at.timestamp())
    conn.execute('INSERT INTO StackComments VALUES(?,?,?,?,?)', vs)

def fetch_comment_id(comment_id, conn):
    row = conn.execute(
            'SELECT * FROM StackComments WHERE Id = ?', 
            (comment_id,)).fetchone()
    return comment_from_db(row)
    

def post_from_xml(xml):
    tags = {}
    if 'Tags' in xml:
        tags = set(re.findall('<(.*?)>', xml['Tags']))
    if 'OwnerUserId' in xml:
        return Post(
                id=xml['Id'],
                score=xml['Score'],
                owner_user_id=xml['OwnerUserId'],
                parent_id= xml.get('ParentId', None),
                created_at=parse_date(xml['CreationDate']),
                tags=tags)

def post_from_db(row, conn):
    (p_id, score, owner_id, parent_id, created_at_stamp) = row
    tags = [tag for (tag,) in conn.execute(
        'SELECT Tag FROM StackTagAssignments WHERE PostId = ?',
        (p_id,))]
    return Post(
            id=p_id,
            score=score,
            owner_user_id=owner_id,
            parent_id=parent_id,
            created_at=datetime.utcfromtimestamp(created_at_stamp),
            tags=tags)

def store_post(p, conn):
    values = (p.id, p.score, p.owner_user_id, p.parent_id, p.created_at.timestamp())
    conn.execute('INSERT INTO StackPosts VALUES(?,?,?,?,?)', values)
    for tag in p.tags:
        conn.execute('INSERT INTO StackTagAssignments VALUES(?,?)',
                    (p.id, tag))

def fetch_post_id(post_id, conn):
    row = conn.execute(
            'SELECT * FROM StackPosts WHERE Id = ?',
            (post_id,)).fetchone()
    return post_from_db(row, conn)

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
            print(count / 1000000.0)

def reload_posts(conn):
    print('Deleting post data')
    conn.execute('DELETE FROM StackPosts')
    children = xml_children('data/Posts.xml')
    print('Loading post data')
    for count, child in enumerate(children):
        post = post_from_xml(child)
        if post is not None:
            store_post(post, conn)
        if count % 10000 == 0: 
            print(count / 1000000.0)

def user_fetch_id(user_id, conn):
    row = conn.execute(
            'SELECT * FROM StackUsers WHERE Id = ?',
            (user_id,)).fetchone()
    return User(*row)

def user_fetch_display_name(display_name, conn):
    row = conn.execute(
            'SELECT * FROM StackUsers WHERE DisplayName = ?',
            (display_name,)).fetchone()
    return User(*row)

def user_fetch_display_name_all(display_name, conn):
    rows = conn.execute(
            'SELECT * FROM StackUsers WHERE DisplayName = ?',
            (display_name,)).fetchall()
    return [User(*row) for row in rows]

def user_posts(user, conn):
    return [post_from_db(row, conn) for row in conn.execute(
        'SELECT * FROM StackPosts WHERE OwnerUserId = ?',
        (user.id,))]

def user_comments(user, conn):
    return [comment_from_db(row) for row in conn.execute(
        'SELECT * FROM StackComments WHERE UserId = ?',
        (user.id,))]

def user_answerers(user, conn):
    rows = conn.execute('''
        SELECT answerers.* FROM StackUsers su
        JOIN StackPosts sp ON su.Id = sp.OwnerUserId
        JOIN StackPosts answers ON answers.ParentId = sp.Id
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

user_attribute_schema = {
        'id': 'string',
        'display_name': 'string',
        'reputation': 'integer',
        'website_url': 'string',
        'age': 'integer',
        'location': 'string'}

def user_serialize(user):
    return user._asdict()

def user_label(user):
    return user.display_name

node_visualizer = NodeVisualizer(
        schema=user_attribute_schema,
        serialize=user_serialize,
        label=user_label)

user_walk = Walk(
        out_gen=user_questioners,
        in_gen=user_answerers,
        select_leaves=lambda leaves: leaves)
