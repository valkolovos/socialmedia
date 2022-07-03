from datetime import datetime
from socialmedia import connection_status
from socialmedia.models import CommentReference, Connection, PostReference

def test_constructor():
    post_reference = PostReference(
        connection=Connection(
            host='abc.xyz',
            status=connection_status.CONNECTED,
        ),
        post_id='post_id',
        read=False,
    )
    assert post_reference.connection.host == 'abc.xyz'
    assert post_reference.post_id == 'post_id'
    assert not post_reference.read
    assert type(post_reference.created) == datetime

def test_str():
    post_reference = PostReference(
        connection=Connection(
            host='abc.xyz',
            status=connection_status.CONNECTED,
        ),
        post_id='post_id',
        read=False,
    )
    expected_str = f'connection: {{ {str(post_reference.connection)} }}, ' \
            f'post_id: {post_reference.post_id}, '\
            f'read: {post_reference.read}, created: {post_reference.created}'
    assert str(post_reference) == expected_str

def test_repr():
    post_reference = PostReference(
        connection=Connection(
            host='abc.xyz',
            status=connection_status.CONNECTED,
        ),
        post_id='post_id',
        read=False,
    )
    expected_repr = f'PostReference(connection: {{ {repr(post_reference.connection)} }}, ' \
            f'post_id: {post_reference.post_id}, '\
            f'read: {post_reference.read}, created: {post_reference.created})'
    assert repr(post_reference) == expected_repr

def test_eq():
    post_reference_one = PostReference(
        connection=Connection(
            host='abc.xyz',
            status=connection_status.CONNECTED,
        ),
        post_id='post_id',
        read=False,
    )
    post_reference_one = PostReference(
        connection=Connection(
            id=post_reference_one.connection.id,
            host='abc.xyz',
            status=connection_status.CONNECTED,
            created=post_reference_one.connection.created,
            updated=post_reference_one.connection.updated,
        ),
        post_id='post_id',
        read=True,
        created=datetime(2000, 1, 1, 0, 0)
    )
    # read values are not part of the equality check
    # neither is creation
    assert post_reference_one == post_reference_one

def test_not_eq():
    post_reference_one = PostReference(
        connection=Connection(
            host='abc.xyz',
            status=connection_status.CONNECTED,
        ),
        post_id='post_id',
        read=False,
    )
    post_reference_two = PostReference(
        connection=Connection(
            id=post_reference_one.connection.id,
            host='abc.xyz',
            status=connection_status.CONNECTED,
            created=post_reference_one.connection.created,
            updated=post_reference_one.connection.updated,
        ),
        post_id='different_post_id'
    )
    assert post_reference_one != post_reference_two

def test_post_reference_not_comment_reference():
    # because CommentReference and PostReference share the exact
    # same attributes, need to ensure that they are not considered equal
    comment_reference = CommentReference(
        connection=Connection(
            host='abc.xyz',
            status=connection_status.CONNECTED,
        ),
        post_id='post_id',
        read=False,
    )
    post_reference = PostReference(
        connection=Connection(
            id=comment_reference.connection.id,
            host='abc.xyz',
            status=connection_status.CONNECTED,
            created=comment_reference.connection.created,
            updated=comment_reference.connection.updated,
        ),
        post_id='post_id',
        read=False,
    )
    assert post_reference != comment_reference

