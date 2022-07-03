import json

from collections import namedtuple
from flask import url_for
from io import BytesIO
from unittest import mock

from socialmedia import connection_status
from socialmedia.views.utils import enc_and_sign_payload
from test import datamodels
from .utils import client

MockResponse = namedtuple('NamedResponse', ['status_code', 'content'])

def test_get_posts(client):
    # not adding either of these to test.datamodels
    # because an authenticated_user in the session
    # should not need to be retrieved
    user = datamodels.User(
        email='user@example.com',
        id=datamodels.User.generate_uuid(),
    )
    user.save()
    profile = datamodels.Profile(
        display_name='User',
        handle='handle',
        user_id=user.id,
    )
    profile.save()
    post = datamodels.Post(
        text='Test Post',
        profile=profile,
        files=['attachment.png']
    )
    post.save()
    # need to set a user id in the session
    # this will also call socialmedia.views.auth.load_user
    with client.session_transaction() as sess:
        sess['_user_id'] = user.id
        sess['authenticated_user'] = user.as_json()
        sess['user'] = profile.as_json()
    response = client.get('/get-posts')
    assert response.status_code == 200
    json_response = json.loads(response.data)
    assert len(json_response) == 1
    assert json_response[0]['text'] == post.text
    assert json_response[0]['id'] == post.id
    assert len(json_response[0]['files']) == 1
    assert json_response[0]['files'][0] == 'test_attachment.png'
    assert json_response[0]['profile']['handle'] == profile.handle

def test_create_post(client):
    user = datamodels.User(
        email='user@example.com',
        id=datamodels.User.generate_uuid(),
    )
    user.save()
    profile = datamodels.Profile(
        display_name='User',
        handle='user_handle',
        user_id=user.id,
    )
    profile.save()
    with client.session_transaction() as sess:
        sess['_user_id'] = user.id
        sess['authenticated_user'] = user.as_json()
        sess['user'] = profile.as_json()
    client.get('/')
    response = client.post(url_for('main.create_post'), data={
        'post': 'This is a test post',
        'file-1': (BytesIO(b'file data'), 'filename.txt')
    }, content_type='multipart/form-data')
    assert response.status_code == 200
    post = datamodels.Post.get(profile=profile)
    assert post.text == 'This is a test post'
    # test signed url generator will prepend 'test_'
    assert post.files == ['test_filename.txt']
    client.application.task_manager.queue_task.assert_called_with(
        {
            'post_id': post.id,
        },
        'post-created',
        url_for('queue_workers.post_created')
    )

def test_get_connection_posts(client):
    user = datamodels.User(
        email='user@example.com',
        id=datamodels.User.generate_uuid(),
    )
    user.save()
    profile = datamodels.Profile(
        display_name='User',
        handle='user_handle',
        user_id=user.id,
    )
    profile.save()
    other_user = datamodels.User(
        email='other_user@otherhost.com',
        id=datamodels.User.generate_uuid(),
    )
    other_profile = datamodels.Profile(
        display_name='Other User',
        handle='other_handle',
        user_id=other_user.id,
    )
    connection = datamodels.Connection(
        profile=profile,
        host='other_host.com',
        handle=other_profile.handle,
        display_name=other_profile.display_name,
        public_key=other_profile.public_key,
        status=connection_status.CONNECTED,
    )
    connection.save()
    other_connection = datamodels.Connection(
        profile=other_profile,
        host='localhost',
        handle=profile.handle,
        display_name=profile.display_name,
        public_key=profile.public_key,
        status=connection_status.CONNECTED,
    )
    post = datamodels.Post(
        profile=other_profile,
        text='test_get_connection_posts',
        files=['get_connection_posts_attachment.png']
    )
    enc_payload, enc_key, signature, nonce, tag = enc_and_sign_payload(
        other_profile, other_connection, [post.as_json()]
    )
    with client.session_transaction() as sess:
        sess['_user_id'] = user.id
        sess['authenticated_user'] = user.as_json()
        sess['user'] = profile.as_json()
    with mock.patch('socialmedia.views.main.requests') as req:
        req.post.return_value = MockResponse(
            200,
            json.dumps({
                'enc_payload': enc_payload,
                'enc_key': enc_key,
                'signature': signature,
                'nonce': nonce,
                'tag': tag
            })
        )
        client.get('/')
        response = client.get(
            url_for('main.get_connection_posts', connection_id=connection.id)
        )
        assert response.status_code == 200
        json_response = response.json
        assert len(json_response) == 1
        json_post = json_response[0]
        assert json_post['text'] == post.text
        assert len(json_post['files']) == 1
        assert json_post['files'][0] == 'get_connection_posts_attachment.png'
        assert json_post['profile']['handle'] == other_profile.handle

def test_get_connection_posts_no_connection(client):
    user = datamodels.User(
        email='user@example.com',
        id=datamodels.User.generate_uuid(),
    )
    user.save()
    profile = datamodels.Profile(
        display_name='User',
        handle='user_handle',
        user_id=user.id,
    )
    profile.save()
    with client.session_transaction() as sess:
        sess['_user_id'] = user.id
        sess['authenticated_user'] = user.as_json()
        sess['user'] = profile.as_json()
    client.get('/')
    response = client.get(
        url_for('main.get_connection_posts', connection_id='mock_connection')
    )
    assert response.status_code == 404
    assert response.data == b'No connection found (mock_connection)'

def test_get_connection_posts_failed_response(client):
    user = datamodels.User(
        email='user@example.com',
        id=datamodels.User.generate_uuid(),
    )
    user.save()
    profile = datamodels.Profile(
        display_name='User',
        handle='user_handle',
        user_id=user.id,
    )
    profile.save()
    other_user = datamodels.User(
        email='other_user@otherhost.com',
        id=datamodels.User.generate_uuid(),
    )
    other_profile = datamodels.Profile(
        display_name='Other User',
        handle='other_handle',
        user_id=other_user.id,
    )
    connection = datamodels.Connection(
        profile=profile,
        host='other_host.com',
        handle=other_profile.handle,
        display_name=other_profile.display_name,
        public_key=other_profile.public_key,
        status=connection_status.CONNECTED,
    )
    connection.save()
    with client.session_transaction() as sess:
        sess['_user_id'] = user.id
        sess['authenticated_user'] = user.as_json()
        sess['user'] = profile.as_json()
    with mock.patch('socialmedia.views.main.requests') as req:
        req.post.return_value = MockResponse(404, 'No connection found')
        client.get('/')
        response = client.get(
            url_for('main.get_connection_posts', connection_id=connection.id)
        )
        assert response.status_code == 404
        assert response.data == b'Failed to retrieve connection posts'

def test_get_connection_posts_bad_response(client):
    user = datamodels.User(
        email='user@example.com',
        id=datamodels.User.generate_uuid(),
    )
    user.save()
    profile = datamodels.Profile(
        display_name='User',
        handle='user_handle',
        user_id=user.id,
    )
    profile.save()
    other_user = datamodels.User(
        email='other_user@otherhost.com',
        id=datamodels.User.generate_uuid(),
    )
    other_profile = datamodels.Profile(
        display_name='Other User',
        handle='other_handle',
        user_id=other_user.id,
    )
    connection = datamodels.Connection(
        profile=profile,
        host='other_host.com',
        handle=other_profile.handle,
        display_name=other_profile.display_name,
        public_key=other_profile.public_key,
        status=connection_status.CONNECTED,
    )
    connection.save()
    other_connection = datamodels.Connection(
        profile=other_profile,
        host='localhost',
        handle=profile.handle,
        display_name=profile.display_name,
        public_key=profile.public_key,
        status=connection_status.CONNECTED,
    )
    post = datamodels.Post(
        profile=other_profile,
        text='test_get_connection_posts',
        files=['get_connection_posts_attachment.png']
    )
    with client.session_transaction() as sess:
        sess['_user_id'] = user.id
        sess['authenticated_user'] = user.as_json()
        sess['user'] = profile.as_json()
    with mock.patch('socialmedia.views.main.requests') as req:
        req.post.return_value = MockResponse(
            200,
            json.dumps(post.as_json())
        )
        client.get('/')
        response = client.get(
            url_for('main.get_connection_posts', connection_id=connection.id)
        )
        assert response.status_code == 500
        assert response.data == b"Failed to decode response: 'enc_key'"

def test_mark_post_read(client):
    user = datamodels.User(
        email='user@example.com',
        id=datamodels.User.generate_uuid(),
    )
    user.save()
    profile = datamodels.Profile(
        display_name='User',
        handle='user_handle',
        user_id=user.id,
    )
    profile.save()
    other_user = datamodels.User(
        email='other_user@otherhost.com',
        id=datamodels.User.generate_uuid(),
    )
    other_profile = datamodels.Profile(
        display_name='Other User',
        handle='other_handle',
        user_id=other_user.id,
    )
    connection = datamodels.Connection(
        profile=profile,
        host='other_host.com',
        handle=other_profile.handle,
        display_name=other_profile.display_name,
        public_key=other_profile.public_key,
        status=connection_status.CONNECTED,
    )
    connection.save()
    post_reference = datamodels.PostReference(
        connection=connection,
        post_id='mock_post_id',
    )
    post_reference.save()
    with client.session_transaction() as sess:
        sess['_user_id'] = user.id
        sess['authenticated_user'] = user.as_json()
        sess['user'] = profile.as_json()
    client.get('/')
    response = client.get(
        url_for('main.mark_post_read', post_id=post_reference.post_id)
    )
    assert response.status_code == 200
    assert post_reference.read

def test_mark_post_read_no_notification(client):
    user = datamodels.User(
        email='user@example.com',
        id=datamodels.User.generate_uuid(),
    )
    user.save()
    profile = datamodels.Profile(
        display_name='User',
        handle='user_handle',
        user_id=user.id,
    )
    profile.save()
    with client.session_transaction() as sess:
        sess['_user_id'] = user.id
        sess['authenticated_user'] = user.as_json()
        sess['user'] = profile.as_json()
    client.get('/')
    response = client.get(
        url_for('main.mark_post_read', post_id='does not exist')
    )
    assert response.status_code == 404
    assert response.data == b'No such post id (does not exist)'

def test_add_comment(client):
    user = datamodels.User(
        email='user@example.com',
        id=datamodels.User.generate_uuid(),
    )
    user.save()
    profile = datamodels.Profile(
        display_name='User',
        handle='user_handle',
        user_id=user.id,
    )
    profile.save()
    other_user = datamodels.User(
        email='other_user@otherhost.com',
        id=datamodels.User.generate_uuid(),
    )
    other_profile = datamodels.Profile(
        display_name='Other User',
        handle='other_handle',
        user_id=other_user.id,
    )
    connection = datamodels.Connection(
        profile=profile,
        host='other_host.com',
        handle=other_profile.handle,
        display_name=other_profile.display_name,
        public_key=other_profile.public_key,
        status=connection_status.CONNECTED,
    )
    connection.save()
    with client.session_transaction() as sess:
        sess['_user_id'] = user.id
        sess['authenticated_user'] = user.as_json()
        sess['user'] = profile.as_json()
    post_id = 'mock_post_id'
    comment_text = 'test comment'
    client.get('/')
    response = client.post(
        url_for('main.add_comment', post_id=post_id),
        data={
            'connectionId': connection.id,
            'comment': comment_text,
            'file-1': (BytesIO(b'file data'), 'filename.txt')
        }
    )
    assert response.status_code == 200
    comment = datamodels.Comment.get()
    assert comment is not None
    client.application.task_manager.queue_task.assert_called_with(
        {
            'user_key': profile.user_id,
            'user_host': 'localhost',
            'post_id': post_id,
            'comment_id': comment.id,
            'connection_key': connection.id,
        },
        'comment-created',
        url_for('queue_workers.comment_created')
    )
    assert response.json['post_id'] == post_id
    assert response.json['profile']['user_id'] == user.id
    assert response.json['text'] == comment_text
    assert len(response.json['files']) == 1
    assert response.json['files'][0] == 'test_file-1'

def test_add_comment_no_connection(client):
    user = datamodels.User(
        email='user@example.com',
        id=datamodels.User.generate_uuid(),
    )
    user.save()
    profile = datamodels.Profile(
        display_name='User',
        handle='user_handle',
        user_id=user.id,
    )
    profile.save()
    with client.session_transaction() as sess:
        sess['_user_id'] = user.id
        sess['authenticated_user'] = user.as_json()
        sess['user'] = profile.as_json()
    client.get('/')
    post_id = 'mock_post_id'
    comment = 'test comment'
    response = client.post(
        url_for('main.add_comment', post_id=post_id),
        data={
            'connectionId': 'does not exist',
            'comment': comment
        }
    )
    assert not client.application.task_manager.queue_task.called
    assert response.status_code == 404
    assert response.data == b'Connection id (does not exist) not found'
    assert datamodels.Comment.get() is None
