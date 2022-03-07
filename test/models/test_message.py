import uuid

from datetime import datetime
from sortedcontainers import SortedList

from socialmedia.models import Comment, Message, Profile

def test_constructor():
    message = Message(
        profile=Profile(),
        text='Message Text',
        files=['file1.png'],
    )
    assert uuid.UUID(message.id)
    assert type(message.profile) == Profile
    assert message.text == 'Message Text'
    assert message.files == ['file1.png']
    assert type(message.created) == datetime
    assert isinstance(message.comments, SortedList)

def test_str():
    message = Message(
        profile=Profile(),
        text='Message Text',
        files=['file1.png'],
    )
    expected_str =  f'id: {message.id}, profile: {{ {message.profile} }}, text: {message.text}, ' \
        f'files: {message.files}, created: {message.created}, has_comments: False'
    assert str(message) == expected_str

def test_repr():
    message = Message(
        profile=Profile(),
        text='Message Text',
        files=['file1.png'],
    )
    message.comments.add(
        Comment(
            text='comment text'
        )
    )
    expected_repr = f'Message(id: {message.id}, profile: {{ {message.profile} }}, text: {message.text}, ' \
        f'files: {message.files}, created: {message.created}, comments: {message.comments})'
    assert repr(message) == expected_repr

def test_eq():
    message_one = Message(
        profile=Profile(),
        text='Message Text',
        files=['file1.png'],
    )
    message_two = Message(
        id=message_one.id,
        profile=message_one.profile,
        text='Message Text',
        files=['file1.png'],
        created=message_one.created,
    )
    assert message_one == message_two

def test_not_eq():
    message_one = Message(
        profile=Profile(),
        text='Message Text',
        files=['file1.png'],
    )
    message_two = Message(
        profile=message_one.profile,
        text='Different Text',
        files=['file1.png'],
        created=message_one.created,
    )
    assert message_one != message_two

def test_as_json():
    message = Message(
        profile=Profile(),
        text='Message Text',
        files=['file1.png'],
    )
    message.comments.add(
        Comment(
            profile=message.profile,
            text='comment text'
        )
    )
    assert message.as_json() == {
        'profile': message.profile.as_json(),
        'id': message.id,
        'text': message.text,
        'created': str(message.created),
        'files': message.files,
        'comments': [comment.as_json() for comment in message.comments]
    }
