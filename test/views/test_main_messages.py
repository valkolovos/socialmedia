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

def test_get_messages(client):
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
    message = datamodels.Message(
        text='Test Message',
        profile=profile,
        files=['attachment.png']
    )
    message.save()
    # need to set a user id in the session
    # this will also call socialmedia.views.auth.load_user
    with client.session_transaction() as sess:
        sess['_user_id'] = user.id
        sess['authenticated_user'] = user.as_json()
        sess['user'] = profile.as_json()
    response = client.get('/get-messages')
    assert response.status_code == 200
    json_response = json.loads(response.data)
    assert len(json_response) == 1
    assert json_response[0]['text'] == message.text
    assert json_response[0]['id'] == message.id
    assert len(json_response[0]['files']) == 1
    assert json_response[0]['files'][0] == 'test_attachment.png'
    assert json_response[0]['profile']['handle'] == profile.handle

def test_create_message(client):
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
    response = client.post(url_for('main.create_message'), data={
        'message': 'This is a test message',
        'file-1': (BytesIO(b'file data'), 'filename.txt')
    }, content_type='multipart/form-data')
    assert response.status_code == 200
    message = datamodels.Message.get(profile=profile)
    assert message.text == 'This is a test message'
    # test signed url generator will prepend 'test_'
    assert message.files == ['test_filename.txt']
    client.application.task_manager.queue_task.assert_called_with(
        {
            'message_id': message.id,
        },
        'message-created',
        url_for('queue_workers.message_created')
    )

def test_get_connection_messages(client):
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
    message = datamodels.Message(
        profile=other_profile,
        text='test_get_connection_messages',
        files=['get_connection_messages_attachment.png']
    )
    enc_payload, enc_key, signature, nonce, tag = enc_and_sign_payload(
        other_profile, other_connection, [message.as_json()]
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
            url_for('main.get_connection_messages', connection_id=connection.id)
        )
        assert response.status_code == 200
        json_response = response.json
        assert len(json_response) == 1
        json_message = json_response[0]
        assert json_message['text'] == message.text
        assert len(json_message['files']) == 1
        assert json_message['files'][0] == 'get_connection_messages_attachment.png'
        assert json_message['profile']['handle'] == other_profile.handle

def test_get_connection_messages_no_connection(client):
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
        url_for('main.get_connection_messages', connection_id='mock_connection')
    )
    assert response.status_code == 404
    assert response.data == b'No connection found (mock_connection)'

def test_get_connection_messages_failed_response(client):
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
            url_for('main.get_connection_messages', connection_id=connection.id)
        )
        assert response.status_code == 404
        assert response.data == b'Failed to retrieve connection messages'

def test_get_connection_messages_bad_response(client):
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
    message = datamodels.Message(
        profile=other_profile,
        text='test_get_connection_messages',
        files=['get_connection_messages_attachment.png']
    )
    with client.session_transaction() as sess:
        sess['_user_id'] = user.id
        sess['authenticated_user'] = user.as_json()
        sess['user'] = profile.as_json()
    with mock.patch('socialmedia.views.main.requests') as req:
        req.post.return_value = MockResponse(
            200,
            json.dumps(message.as_json())
        )
        client.get('/')
        response = client.get(
            url_for('main.get_connection_messages', connection_id=connection.id)
        )
        assert response.status_code == 500
        assert response.data == b"Failed to decode response: 'enc_key'"

def test_mark_message_read(client):
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
    message_reference = datamodels.MessageReference(
        connection=connection,
        message_id='mock_message_id',
    )
    message_reference.save()
    with client.session_transaction() as sess:
        sess['_user_id'] = user.id
        sess['authenticated_user'] = user.as_json()
        sess['user'] = profile.as_json()
    client.get('/')
    response = client.get(
        url_for('main.mark_message_read', message_id=message_reference.message_id)
    )
    assert response.status_code == 200
    assert message_reference.read

def test_mark_message_read_no_notification(client):
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
        url_for('main.mark_message_read', message_id='does not exist')
    )
    assert response.status_code == 404
    assert response.data == b'No such message id (does not exist)'

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
    message_id = 'mock_message_id'
    comment_text = 'test comment'
    client.get('/')
    response = client.post(
        url_for('main.add_comment', message_id=message_id),
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
            'message_id': message_id,
            'comment_id': comment.id,
            'connection_key': connection.id,
        },
        'comment-created',
        url_for('queue_workers.comment_created')
    )
    assert response.json['message_id'] == message_id
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
    message_id = 'mock_message_id'
    comment = 'test comment'
    response = client.post(
        url_for('main.add_comment', message_id=message_id),
        data={
            'connectionId': 'does not exist',
            'comment': comment
        }
    )
    assert not client.application.task_manager.queue_task.called
    assert response.status_code == 404
    assert response.data == b'Connection id (does not exist) not found'
    assert datamodels.Comment.get() is None
