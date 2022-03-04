import uuid

from datetime import datetime
from socialmedia.models import Comment, Profile

def test_constructor():
    comment = Comment(
        profile=Profile(
            handle='profile_handle',
            display_name='Profile Display Name',
            user_id='user_id'
        ),
        message_id='message_id',
        text='Test Comment',
        files=['file1.txt']
    )
    assert uuid.UUID(comment.id)
    assert comment.text == 'Test Comment'
    assert comment.message_id == 'message_id'
    assert comment.profile is not None
    assert len(comment.files) == 1
    assert comment.files[0] == 'file1.txt'
    assert type(comment.created) == datetime

def test_str():
    comment = Comment(
        profile=Profile(
            handle='profile_handle',
            display_name='Profile Display Name',
            user_id='user_id'
        ),
        message_id='message_id',
        text='Test Comment',
        files=['file1.txt']
    )
    expected_str = f'id: {comment.id}, message_id: {comment.message_id}, '\
        f'profile: {{ {str(comment.profile)} }}, text: {comment.text}, files: {comment.files}, '\
        f'created: {comment.created}'
    assert str(comment) == expected_str

def test_repr():
    comment = Comment(
        profile=Profile(
            handle='profile_handle',
            display_name='Profile Display Name',
            user_id='user_id'
        ),
        message_id='message_id',
        text='Test Comment',
        files=['file1.txt']
    )
    expected_repr = f'Comment(id: {comment.id}, message_id: {comment.message_id}, '\
        f'profile: {{ {repr(comment.profile)} }}, text: {comment.text}, files: {comment.files}, '\
        f'created: {comment.created})'
    assert repr(comment) == expected_repr

def test_as_json():
    comment = Comment(
        profile=Profile(
            handle='profile_handle',
            display_name='Profile Display Name',
            user_id='user_id'
        ),
        message_id='message_id',
        text='Test Comment',
        files=['file1.txt']
    )
    comment_as_json = comment.as_json()
    assert comment_as_json == {
        'profile': comment.profile.as_json(),
        'id': comment.id,
        'message_id': comment.message_id,
        'text': comment.text,
        'created': str(comment.created),
        'files': comment.files,
    }

def test_eq():
    comment_one = Comment(
        profile=Profile(
            handle='profile_handle',
            display_name='Profile Display Name',
            user_id='user_id'
        ),
        message_id='message_id',
        text='Test Comment',
        files=['file1.txt']
    )
    comment_two = Comment(
        id=comment_one.id,
        profile=comment_one.profile,
        message_id='message_id',
        text='Test Comment',
        files=['file1.txt'],
        created=comment_one.created,
    )
    assert comment_one == comment_two

def test_not_eq():
    comment_one = Comment(
        profile=Profile(
            handle='profile_handle',
            display_name='Profile Display Name',
            user_id='user_id'
        ),
        message_id='message_id',
        text='Test Comment',
        files=['file1.txt']
    )
    comment_two = Comment(
        profile=comment_one.profile,
        message_id='message_id',
        text='Test Comment',
        files=['file1.txt'],
        created=comment_one.created,
    )
    # different ids
    assert comment_one != comment_two
