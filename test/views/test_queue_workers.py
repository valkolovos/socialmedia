from collections import namedtuple
from datetime import datetime, timedelta
from dateutil import tz
from flask import url_for
from unittest import mock
from uuid import UUID

from socialmedia import connection_status
from socialmedia.views.utils import decrypt_payload
from test import datamodels
from .utils import client

MockResponse = namedtuple('NamedResponse', ['status_code', 'content'])

def test_request_connection(client):
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
    with mock.patch('socialmedia.views.queue_workers.requests') as req:
        req.post.return_value = MockResponse(200, None)
        response = client.post(url_for('queue_workers.request_connection'), json={
            'user_host': 'localhost',
            'user_key': user.id,
            'host': 'otherhost.com',
            'handle': 'other_user',
        })
        assert response.status_code == 200
        # effectively asserts profile == profile
        requested_connection = datamodels.Connection.get(profile=profile)
        assert UUID(requested_connection.id, version=4) is not None
        assert requested_connection.host == 'otherhost.com'
        assert requested_connection.handle == 'other_user'
        assert requested_connection.status == connection_status.REQUESTED
        assert req.post.call_args[0][0] == f'https://otherhost.com{url_for("external_comms.request_connection")}'
        assert 'enc_payload' in req.post.call_args[1]['json']
        assert req.post.call_args[1]['json']['handle'] == 'other_user'

def test_request_connection_failed(client):
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
    with mock.patch('socialmedia.views.queue_workers.requests') as req:
        req.post.return_value = MockResponse(500, 'Something went wrong')
        response = client.post(url_for('queue_workers.request_connection'), json={
            'user_host': 'localhost',
            'user_key': user.id,
            'host': 'otherhost.com',
            'handle': 'other_user',
        })
        assert response.status_code == 500
        assert response.data == b'Connection request failed'
        assert not any([type(e) == e for e in datamodels.Profile._data])

def test_ack_connection(client):
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
        status=connection_status.PENDING,
        created=(datetime.now() - timedelta(days=1)).astimezone(tz.UTC),
        updated=(datetime.now() - timedelta(days=1)).astimezone(tz.UTC),
    )
    connection.save()
    with mock.patch('socialmedia.views.queue_workers.requests') as req:
        req.post.return_value = MockResponse(200, None)
        response = client.post(url_for('queue_workers.ack_connection'), json={
            'user_host': 'localhost',
            'user_key': user.id,
            'connection_id': connection.id,
        })
        assert response.status_code == 200
        assert connection.status == connection_status.CONNECTED
        assert connection.updated > connection.created
        assert req.post.call_count == 1
        assert req.post.call_args[0][0] == f'https://other_host.com{url_for("external_comms.ack_connection")}'
        assert req.post.call_args[1]['json']['handle'] == connection.handle
        request_data = req.post.call_args[1]['json']
        request_payload = decrypt_payload(
            other_profile,
            request_data['enc_key'],
            request_data['enc_payload'],
            request_data['nonce'],
            request_data['tag'],
        )
        assert request_payload['ack_host'] == 'localhost'
        assert request_payload['ack_handle'] == profile.handle
        assert request_payload['ack_display_name'] == profile.display_name
        assert request_payload['ack_public_key'] == profile.public_key.decode()

def test_ack_connection_no_valid_connection(client):
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
    other_user = datamodels.User(
        email='other_user@otherhost.com',
        id=datamodels.User.generate_uuid(),
    )
    other_profile = datamodels.Profile(
        display_name='Other User',
        handle='other_handle',
        user_id=other_user.id,
    )
    with mock.patch('socialmedia.views.queue_workers.requests') as req:
        req.post.return_value = MockResponse(200, None)
        response = client.post(url_for('queue_workers.ack_connection'), json={
            'user_host': 'localhost',
            'user_key': user.id,
            'connection_id': 'invalid_connection'
        })
        assert response.status_code == 404
        assert response.data == b'No connection invalid_connection found for user handle'
        assert not req.post.called

def test_ack_connection_reply_failed(client):
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
    other_user = datamodels.User(
        email='other_user@otherhost.com',
        id=datamodels.User.generate_uuid(),
    )
    other_profile = datamodels.Profile(
        display_name='Other User',
        handle='other_handle',
        user_id=other_user.id,
    )
    created = (datetime.now() - timedelta(days=1)).astimezone(tz.UTC)
    connection = datamodels.Connection(
        profile=profile,
        host='other_host.com',
        handle=other_profile.handle,
        display_name=other_profile.display_name,
        public_key=other_profile.public_key,
        status=connection_status.PENDING,
        created=created,
        updated=created,
    )
    connection.save()
    with mock.patch('socialmedia.views.queue_workers.requests') as req:
        req.post.return_value = MockResponse(404, 'Connection not found')
        response = client.post(url_for('queue_workers.ack_connection'), json={
            'user_host': 'localhost',
            'user_key': user.id,
            'connection_id': connection.id,
        })
        assert response.status_code == 404
        assert response.data == b'Failed to ack requested connection'
        assert connection.status == connection_status.PENDING
        assert connection.updated == connection.created

def test_post_created(client):
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
    connection_one = datamodels.Connection(
        profile=profile,
        host='other_host.com',
        handle='other_handle',
        display_name='Other Name',
        status=connection_status.CONNECTED,
    )
    connection_one.save()
    connection_two = datamodels.Connection(
        profile=profile,
        host='different_host.com',
        handle='different_handle',
        display_name='Different Name',
        status=connection_status.CONNECTED,
    )
    connection_two.save()
    post = datamodels.Post(
        profile=profile,
        text='Post Text',
    )
    post.save()
    response = client.post(url_for('queue_workers.post_created'), json={
        'post_id': post.id,
    })
    assert response.status_code == 200
    assert client.application.task_manager.queue_task.call_count == 2
    client.application.task_manager.queue_task.assert_any_call(
        {
            'user_key': post.profile.user_id,
            'post_id': post.id,
            'connection_key': connection_one.id,
        },
        'post-notify',
        url_for('queue_workers.post_notify')
    )
    client.application.task_manager.queue_task.assert_any_call(
        {
            'user_key': post.profile.user_id,
            'post_id': post.id,
            'connection_key': connection_two.id,
        },
        'post-notify',
        url_for('queue_workers.post_notify')
    )

def test_post_created_no_such_post(client):
    response = client.post(url_for('queue_workers.post_created'), json={
        'post_id': 'bogus',
    })
    assert response.status_code == 404
    assert response.data == bytes(f'post bogus not found', encoding='utf-8')
    assert client.application.task_manager.queue_task.call_count == 0

def test_post_notify(client):
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
        handle='other_handle',
        display_name='Other Name',
        status=connection_status.CONNECTED,
        public_key=other_profile.public_key,
    )
    connection.save()
    with mock.patch('socialmedia.views.queue_workers.requests') as req:
        req.post.return_value = MockResponse(200, None)
        response = client.post(url_for('queue_workers.post_notify'), json={
            'user_key': user.id,
            'post_id': 'mock_post_id',
            'connection_key': connection.id,
        })
        assert response.status_code == 200
        assert req.post.call_count == 1
        assert req.post.call_args[0][0] == f'https://other_host.com{url_for("external_comms.post_notify")}'
        assert req.post.call_args[1]['json']['handle'] == connection.handle
        request_data = req.post.call_args[1]['json']
        request_payload = decrypt_payload(
            other_profile,
            request_data['enc_key'],
            request_data['enc_payload'],
            request_data['nonce'],
            request_data['tag'],
        )
        assert request_payload['post_host'] == 'localhost'
        assert request_payload['post_handle'] == 'handle'
        assert request_payload['post_id'] == 'mock_post_id'

def test_post_notify_failed(client):
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
        handle='other_handle',
        display_name='Other Name',
        status=connection_status.CONNECTED,
        public_key=other_profile.public_key,
    )
    connection.save()
    with mock.patch('socialmedia.views.queue_workers.requests') as req:
        req.post.return_value = MockResponse(500, b'Oops')
        response = client.post(url_for('queue_workers.post_notify'), json={
            'user_key': user.id,
            'post_id': 'mock_post_id',
            'connection_key': connection.id,
        })
        assert response.status_code == 500
        assert req.post.call_count == 1

def test_comment_created(client):
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
        handle='other_handle',
        display_name='Other Name',
        status=connection_status.CONNECTED,
        public_key=other_profile.public_key,
    )
    connection.save()
    with mock.patch('socialmedia.views.queue_workers.requests') as req:
        req.post.return_value = MockResponse(200, None)
        response = client.post(url_for('queue_workers.comment_created'), json={
            'user_key': profile.user_id,
            'user_host': 'localhost',
            'post_id': 'post_id',
            'comment_id': 'comment_id',
            'connection_key': connection.id,
        })
        assert response.status_code == 200
        assert response.data == b'Connection other_handle@other_host.com notified of comment post_id on post comment_id'

def test_comment_created_notification_failed(client):
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
        handle='other_handle',
        display_name='Other Name',
        status=connection_status.CONNECTED,
        public_key=other_profile.public_key,
    )
    connection.save()
    with mock.patch('socialmedia.views.queue_workers.requests') as req:
        req.post.return_value = MockResponse(404, 'Connection not found')
        response = client.post(url_for('queue_workers.comment_created'), json={
            'user_key': profile.user_id,
            'user_host': 'localhost',
            'post_id': 'post_id',
            'comment_id': 'comment_id',
            'connection_key': connection.id,
        })
        assert response.status_code == 404
        assert response.data == b'New comment notify failed 404:Connection not found'
