import json

from unittest import mock

from collections import namedtuple
from flask import url_for
from flask_login import AUTH_HEADER_NAME

from socialmedia import connection_status
from socialmedia.views.utils import enc_and_sign_payload
from test import datamodels
from .utils import client, create_token

MockResponse = namedtuple('NamedResponse', ['status_code', 'content'])

def test_request_connection(client):
    admin_user = datamodels.User(
        email='admin@example.com',
        id=datamodels.User.generate_uuid(),
        admin=True,
    )
    admin_user.save()
    admin_profile = datamodels.Profile(
        display_name='Admin User',
        handle='admin_handle',
        user_id=admin_user.id,
    )
    admin_profile.save()
    token = create_token(client, admin_user)
    response = client.post(url_for('main.request_connection'), data={
        'host': 'otherhost.com',
        'handle': 'other_user',
        }, headers={AUTH_HEADER_NAME: token})
    assert response.status_code == 200
    client.application.task_manager.queue_task.assert_called_with(
        {
            'user_host': 'localhost',
            'user_key': admin_user.id,
            'host': 'otherhost.com',
            'handle': 'other_user'
        },
        'request-connection',
        '/worker/request-connection'
    )

def test_reequest_connection_not_logged_in(client):
    response = client.post(url_for('main.request_connection'), data={
        'host': 'otherhost.com',
        'handle': 'other_user',
    })
    assert response.status_code == 401

def test_manage_connection_connect(client):
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
        host='https://other_host.com',
        handle=other_profile.handle,
        display_name=other_profile.display_name,
        public_key=other_profile.public_key,
        status=connection_status.PENDING,
        read=False,
    )
    connection.save()
    token = create_token(client, user)
    response = client.post(url_for('main.manage_connection'), data={
        'connection_id': connection.id,
        'action': 'connect',
        }, headers={AUTH_HEADER_NAME: token})
    assert response.status_code == 200
    client.application.task_manager.queue_task.assert_called_with(
        {
            'user_host': 'localhost',
            'user_key': user.id,
            'connection_id': connection.id,
        },
        'ack-connection',
        url_for('queue_workers.ack_connection')
    )
    assert connection.status == connection_status.CONNECTED
    assert connection.read

def test_manage_connection_delete(client):
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
        host='https://other_host.com',
        handle=other_profile.handle,
        display_name=other_profile.display_name,
        public_key=other_profile.public_key,
        status=connection_status.PENDING,
    )
    connection.save()
    token = create_token(client, user)
    response = client.post(url_for('main.manage_connection'), data={
        'connection_id': connection.id,
        'action': 'delete',
        }, headers={AUTH_HEADER_NAME: token})
    assert response.status_code == 200
    assert not any([e == connection for e in datamodels.Connection._data])

def test_manage_connection_decline(client):
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
        host='https://other_host.com',
        handle=other_profile.handle,
        display_name=other_profile.display_name,
        public_key=other_profile.public_key,
        status=connection_status.PENDING,
    )
    connection.save()
    token = create_token(client, user)
    response = client.post(url_for('main.manage_connection'), data={
        'connection_id': connection.id,
        'action': 'decline',
        }, headers={AUTH_HEADER_NAME: token})
    assert response.status_code == 200
    assert connection.status == connection_status.DECLINED

def test_manage_connection_invalid_action(client):
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
        host='https://other_host.com',
        handle=other_profile.handle,
        display_name=other_profile.display_name,
        public_key=other_profile.public_key,
        status=connection_status.PENDING,
    )
    connection.save()
    token = create_token(client, user)
    response = client.post(url_for('main.manage_connection'), data={
        'connection_id': connection.id,
        'action': 'invalid',
        }, headers={AUTH_HEADER_NAME: token})
    assert response.status_code == 400
    assert response.data == b'Invalid action requested - invalid'

def test_manage_connection_not_logged_in(client):
    response = client.post(url_for('main.manage_connection'), data={
        'host': 'otherhost.com',
        'handle': 'other_user',
    })
    assert response.status_code == 401

def test_manage_connection_invalid_id(client):
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
    token = create_token(client, user)
    response = client.post(url_for('main.manage_connection'), data={
        'action': 'connect',
        }, headers={AUTH_HEADER_NAME: token})
    assert response.status_code == 400

def test_manage_connection_missing_connection(client):
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
    token = create_token(client, user)
    response = client.post(url_for('main.manage_connection'), data={
        'connection_id': 'missing_connection',
        'action': 'decline',
        }, headers={AUTH_HEADER_NAME: token})
    assert response.status_code == 404

def test_get_connection_info(client):
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
    other_user_one = datamodels.User(
        email='other_user@otherhost.com',
        id=datamodels.User.generate_uuid(),
    )
    other_profile_one = datamodels.Profile(
        display_name='Other User One',
        handle='other_handle_one',
        user_id=other_user_one.id,
    )
    connection_one = datamodels.Connection(
        profile=profile,
        host='other_host.com',
        handle=other_profile_one.handle,
        display_name=other_profile_one.display_name,
        public_key=other_profile_one.public_key,
        status=connection_status.CONNECTED,
    )
    connection_one.save()
    other_connection_one = datamodels.Connection(
        profile=other_profile_one,
        host='localhost',
        handle=profile.handle,
        display_name=profile.handle,
        public_key=profile.public_key,
        status=connection_status.CONNECTED,
    )
    post_reference_one = datamodels.PostReference(
        connection=connection_one,
        post_id='mock_post_id_one',
        reference_read=False,
        read=False
    )
    post_reference_one.save()
    other_user_two = datamodels.User(
        email='other_user@different_host.com',
        id=datamodels.User.generate_uuid(),
    )
    other_profile_two = datamodels.Profile(
        display_name='Other User Two',
        handle='other_handle_two',
        user_id=other_user_two.id,
    )
    connection_two = datamodels.Connection(
        profile=profile,
        host='different_host.com',
        handle=other_profile_two.handle,
        display_name=other_profile_two.display_name,
        public_key=other_profile_two.public_key,
        status=connection_status.CONNECTED,
    )
    connection_two.save()
    other_connection_two = datamodels.Connection(
        profile=other_profile_two,
        host='localhost',
        handle=profile.handle,
        display_name=profile.handle,
        public_key=profile.public_key,
        status=connection_status.CONNECTED,
    )
    post_reference_two = datamodels.PostReference(
        connection=connection_two,
        post_id='mock_post_id_two',
        reference_read=True,
        read=True,
    )
    post_reference_two.save()
    declined_user = datamodels.User(
        email='declined_user@different_host.com',
        id=datamodels.User.generate_uuid(),
    )
    declined_profile = datamodels.Profile(
        display_name='Declined User',
        handle='declined_user',
        user_id=declined_user.id,
    )
    declined_connection = datamodels.Connection(
        profile=profile,
        host='different_host.com',
        handle=declined_profile.handle,
        display_name=declined_profile.display_name,
        public_key=declined_profile.public_key,
        status=connection_status.DECLINED,
    )
    declined_connection.save()
    # this is a connection where the primary user
    # has requested a connection with another user
    requested_user = datamodels.User(
        email='requested_user@different_host.com',
        id=datamodels.User.generate_uuid(),
    )
    requested_profile = datamodels.Profile(
        display_name='Requested User',
        handle='requested_handle',
        user_id=requested_user.id,
    )
    requested_connection = datamodels.Connection(
        profile=profile,
        host='different_host.com',
        handle=requested_profile.handle,
        display_name=requested_profile.display_name,
        public_key=requested_profile.public_key,
        status=connection_status.REQUESTED,
    )
    requested_connection.save()
    # this is a connection where another user has requested
    # a connection with the primary user
    pending_connection = datamodels.Connection(
        profile=profile,
        host='different_host.com',
        handle='requesting_user',
        display_name='A Requesting User',
        public_key='mock public key',
        status=connection_status.PENDING,
    )
    pending_connection.save()
    enc_payload_one, enc_key_one, signature_one, nonce_one, tag_one = enc_and_sign_payload(
        other_profile_one, other_connection_one, {'post_count': 1}
    )
    enc_payload_two, enc_key_two, signature_two, nonce_two, tag_two = enc_and_sign_payload(
        other_profile_two, other_connection_two, {'post_count': 1}
    )

    with mock.patch('socialmedia.views.main.requests') as req:
        req.post.side_effect = [
            MockResponse(
                200,
                json.dumps({
                    'enc_payload': enc_payload_one,
                    'enc_key': enc_key_one,
                    'signature': signature_one,
                    'nonce': nonce_one,
                    'tag': tag_one
                })
            ),
            MockResponse(
                200,
                json.dumps({
                    'enc_payload': enc_payload_two,
                    'enc_key': enc_key_two,
                    'signature': signature_two,
                    'nonce': nonce_two,
                    'tag': tag_two
                })
            ),
        ]
        token = create_token(client, user)
        response = client.get(url_for('main.get_connection_info'), headers={AUTH_HEADER_NAME: token})
    assert response.status_code == 200
    json_response = json.loads(response.data)
    assert len(json_response['connections']) == 3
    assert len(json_response['post_references']) == 2
    assert_dict = {}
    post_reference_dict = {
        post_reference['post_id']: post_reference
        for post_reference in json_response['post_references']
    }
    for conn in json_response['connections']:
        assert_dict[conn['handle']] = conn

    assert not post_reference_dict[post_reference_one.post_id]['read']
    assert not post_reference_dict[post_reference_one.post_id]['reference_read']
    assert post_reference_dict[post_reference_two.post_id]['read']
    assert post_reference_dict[post_reference_two.post_id]['reference_read']

    assert assert_dict['other_handle_one']['display_name'] == connection_one.display_name
    assert assert_dict['other_handle_one']['host'] == connection_one.host
    assert assert_dict['other_handle_one']['id'] == connection_one.id
    assert assert_dict['other_handle_one']['status'] == connection_one.status
    assert len(assert_dict['other_handle_one']['post_references']) == 1
    assert not assert_dict['other_handle_one']['post_references'][0]['read']
    assert not assert_dict['other_handle_one']['post_references'][0]['reference_read']

    assert assert_dict['other_handle_two']['display_name'] == connection_two.display_name
    assert assert_dict['other_handle_two']['host'] == connection_two.host
    assert assert_dict['other_handle_two']['id'] == connection_two.id
    assert assert_dict['other_handle_two']['status'] == connection_two.status
    assert len(assert_dict['other_handle_two']['post_references']) == 1
    assert assert_dict['other_handle_two']['post_references'][0]['read'] == True
    assert assert_dict['other_handle_two']['post_references'][0]['reference_read'] == True

    assert assert_dict['requesting_user']['display_name'] == pending_connection.display_name
    assert assert_dict['requesting_user']['host'] == pending_connection.host
    assert assert_dict['requesting_user']['id'] == pending_connection.id
    assert assert_dict['requesting_user']['status'] == pending_connection.status
    assert len(assert_dict['requesting_user']['post_references']) == 0
