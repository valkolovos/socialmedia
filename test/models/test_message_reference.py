from datetime import datetime
from socialmedia.models import CommentReference, Connection, MessageReference

def test_constructor():
    message_reference = MessageReference(
        connection=Connection(
            host='abc.xyz',
        ),
        message_id='message_id',
        read=False,
    )
    assert message_reference.connection.host == 'abc.xyz'
    assert message_reference.message_id == 'message_id'
    assert not message_reference.read
    assert type(message_reference.created) == datetime

def test_str():
    message_reference = MessageReference(
        connection=Connection(
            host='abc.xyz',
        ),
        message_id='message_id',
        read=False,
    )
    expected_str = f'connection: {{ {str(message_reference.connection)} }}, ' \
            f'message_id: {message_reference.message_id}, '\
            f'read: {message_reference.read}, created: {message_reference.created}'
    assert str(message_reference) == expected_str

def test_repr():
    message_reference = MessageReference(
        connection=Connection(
            host='abc.xyz',
        ),
        message_id='message_id',
        read=False,
    )
    expected_repr = f'MessageReference(connection: {{ {repr(message_reference.connection)} }}, ' \
            f'message_id: {message_reference.message_id}, '\
            f'read: {message_reference.read}, created: {message_reference.created})'
    assert repr(message_reference) == expected_repr

def test_eq():
    message_reference_one = MessageReference(
        connection=Connection(
            host='abc.xyz',
        ),
        message_id='message_id',
        read=False,
    )
    message_reference_one = MessageReference(
        connection=Connection(
            id=message_reference_one.connection.id,
            host='abc.xyz',
            created=message_reference_one.connection.created,
            updated=message_reference_one.connection.updated,
        ),
        message_id='message_id',
        read=True,
        created=datetime(2000, 1, 1, 0, 0)
    )
    # read values are not part of the equality check
    # neither is creation
    assert message_reference_one == message_reference_one

def test_not_eq():
    message_reference_one = MessageReference(
        connection=Connection(
            host='abc.xyz',
        ),
        message_id='message_id',
        read=False,
    )
    message_reference_two = MessageReference(
        connection=Connection(
            id=message_reference_one.connection.id,
            host='abc.xyz',
            created=message_reference_one.connection.created,
            updated=message_reference_one.connection.updated,
        ),
        message_id='different_message_id'
    )
    assert message_reference_one != message_reference_two

def test_message_reference_not_comment_reference():
    # because CommentReference and MessageReference share the exact
    # same attributes, need to ensure that they are not considered equal
    comment_reference = CommentReference(
        connection=Connection(
            host='abc.xyz',
        ),
        message_id='message_id',
        read=False,
    )
    message_reference = MessageReference(
        connection=Connection(
            id=comment_reference.connection.id,
            host='abc.xyz',
            created=comment_reference.connection.created,
            updated=comment_reference.connection.updated,
        ),
        message_id='message_id',
        read=False,
    )
    assert message_reference != comment_reference

