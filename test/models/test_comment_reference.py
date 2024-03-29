from datetime import datetime
from socialmedia import connection_status
from socialmedia.models import CommentReference, Connection, PostReference

def test_constructor():
    comment_reference = CommentReference(
        connection=Connection(
            host='abc.xyz',
            status=connection_status.CONNECTED,
        ),
        post_id='post_id',
        read=False,
    )
    assert comment_reference.connection.host == 'abc.xyz'
    assert comment_reference.post_id == 'post_id'
    assert not comment_reference.read
    assert type(comment_reference.created) == datetime

def test_str():
    comment_reference = CommentReference(
        connection=Connection(
            host='abc.xyz',
            status=connection_status.CONNECTED,
        ),
        post_id='post_id',
        read=False,
    )
    expected_str = f'connection: {{ {str(comment_reference.connection)} }}, ' \
            f'post_id: {comment_reference.post_id}, '\
            f'read: {comment_reference.read}, created: {comment_reference.created}'
    assert str(comment_reference) == expected_str

def test_repr():
    comment_reference = CommentReference(
        connection=Connection(
            host='abc.xyz',
            status=connection_status.CONNECTED,
        ),
        post_id='post_id',
        read=False,
    )
    expected_repr = f'CommentReference(connection: {{ {repr(comment_reference.connection)} }}, ' \
            f'post_id: {comment_reference.post_id}, '\
            f'read: {comment_reference.read}, created: {comment_reference.created})'
    assert repr(comment_reference) == expected_repr

def test_eq():
    comment_reference_one = CommentReference(
        connection=Connection(
            host='abc.xyz',
            status=connection_status.CONNECTED,
        ),
        post_id='post_id',
        read=False,
    )
    comment_reference_two = CommentReference(
        connection=Connection(
            id=comment_reference_one.connection.id,
            host='abc.xyz',
            status=connection_status.CONNECTED,
            created=comment_reference_one.connection.created,
            updated=comment_reference_one.connection.updated,
        ),
        post_id='post_id',
        read=True,
        created=datetime(2000, 1, 1, 0, 0)
    )
    # read values are not part of the equality check
    # neither is creation
    assert comment_reference_one == comment_reference_two

def test_not_eq():
    comment_reference_one = CommentReference(
        connection=Connection(
            host='abc.xyz',
            status=connection_status.CONNECTED,
        ),
        post_id='post_id',
        read=False,
    )
    comment_reference_two = CommentReference(
        connection=Connection(
            id=comment_reference_one.connection.id,
            host='abc.xyz',
            status=connection_status.CONNECTED,
            created=comment_reference_one.connection.created,
            updated=comment_reference_one.connection.updated,
        ),
        post_id='different_post_id'
    )
    assert comment_reference_one != comment_reference_two

def test_post_reference_not_comment_reference():
    # because CommentReference and postReference share the exact
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
    assert comment_reference != post_reference
