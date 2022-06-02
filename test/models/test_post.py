import uuid

from datetime import datetime
from sortedcontainers import SortedList

from socialmedia.models import Comment, Post, Profile

def test_constructor():
    post = Post(
        profile=Profile(),
        text='Post Text',
        files=['file1.png'],
    )
    assert uuid.UUID(post.id)
    assert type(post.profile) == Profile
    assert post.text == 'Post Text'
    assert post.files == ['file1.png']
    assert type(post.created) == datetime
    assert isinstance(post.comments, SortedList)

def test_str():
    post = Post(
        profile=Profile(),
        text='Post Text',
        files=['file1.png'],
    )
    expected_str =  f'id: {post.id}, profile: {{ {post.profile} }}, text: {post.text}, ' \
        f'files: {post.files}, created: {post.created}, has_comments: False'
    assert str(post) == expected_str

def test_repr():
    post = Post(
        profile=Profile(),
        text='Post Text',
        files=['file1.png'],
    )
    post.comments.add(
        Comment(
            text='comment text'
        )
    )
    expected_repr = f'Post(id: {post.id}, profile: {{ {post.profile} }}, text: {post.text}, ' \
        f'files: {post.files}, created: {post.created}, comments: {post.comments})'
    assert repr(post) == expected_repr

def test_eq():
    post_one = Post(
        profile=Profile(),
        text='Post Text',
        files=['file1.png'],
    )
    post_two = Post(
        id=post_one.id,
        profile=post_one.profile,
        text='Post Text',
        files=['file1.png'],
        created=post_one.created,
    )
    assert post_one == post_two

def test_not_eq():
    post_one = Post(
        profile=Profile(),
        text='Post Text',
        files=['file1.png'],
    )
    post_two = Post(
        profile=post_one.profile,
        text='Different Text',
        files=['file1.png'],
        created=post_one.created,
    )
    assert post_one != post_two

def test_as_json():
    post = Post(
        profile=Profile(),
        text='Post Text',
        files=['file1.png'],
    )
    post.comments.add(
        Comment(
            profile=post.profile,
            text='comment text'
        )
    )
    assert post.as_json() == {
        'profile': post.profile.as_json(),
        'id': post.id,
        'text': post.text,
        'created': str(post.created),
        'files': post.files,
        'comments': [comment.as_json() for comment in post.comments]
    }
