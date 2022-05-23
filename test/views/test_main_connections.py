import json

from flask import url_for

from socialmedia import connection_status
from test import datamodels
from .utils import client

def test_request_connection(client):
    # not adding either of these to test.datamodels
    # because an authenticated_user in the session
    # should not need to be retrieved
    admin_user = datamodels.User(
        email='admin@example.com',
        id=datamodels.User.generate_uuid(),
        admin=True,
    )
    admin_profile = datamodels.Profile(
        display_name='Admin User',
        handle='admin_handle',
        user_id=admin_user.id,
    )
    # need to set a user id in the session
    # this will also call socialmedia.views.auth.load_user
    with client.session_transaction() as sess:
        sess['_user_id'] = admin_user.id
        sess['authenticated_user'] = admin_user.as_json()
        sess['user'] = admin_profile.as_json()
    # need to re-request '/' to re-initialize the app context
    # because the session transaction above destroys the context
    client.get('/')
    response = client.post(url_for('main.request_connection'), data={
        'host': 'otherhost.com',
        'handle': 'other_user',
    })
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
    profile = datamodels.Profile(
        display_name='User',
        handle='handle',
        user_id=user.id,
    )
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
    # need to set a user id in the session
    # this will also call socialmedia.views.auth.load_user
    with client.session_transaction() as sess:
        sess['_user_id'] = user.id
        sess['authenticated_user'] = user.as_json()
        sess['user'] = profile.as_json()
    # need to re-request '/' to re-initialize the app context
    # because the session transaction above destroys the context
    client.get('/')
    response = client.post(url_for('main.manage_connection'), data={
        'connection_id': connection.id,
        'action': 'connect',
    })
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

def test_manage_connection_delete(client):
    user = datamodels.User(
        email='user@example.com',
        id=datamodels.User.generate_uuid(),
    )
    profile = datamodels.Profile(
        display_name='User',
        handle='handle',
        user_id=user.id,
    )
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
    # need to set a user id in the session
    # this will also call socialmedia.views.auth.load_user
    with client.session_transaction() as sess:
        sess['_user_id'] = user.id
        sess['authenticated_user'] = user.as_json()
        sess['user'] = profile.as_json()
    # need to re-request '/' to re-initialize the app context
    # because the session transaction above destroys the context
    client.get('/')
    response = client.post(url_for('main.manage_connection'), data={
        'connection_id': connection.id,
        'action': 'delete',
    })
    assert response.status_code == 200
    assert not any([e == connection for e in datamodels.Connection._data])

def test_manage_connection_decline(client):
    user = datamodels.User(
        email='user@example.com',
        id=datamodels.User.generate_uuid(),
    )
    profile = datamodels.Profile(
        display_name='User',
        handle='handle',
        user_id=user.id,
    )
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
    # need to set a user id in the session
    # this will also call socialmedia.views.auth.load_user
    with client.session_transaction() as sess:
        sess['_user_id'] = user.id
        sess['authenticated_user'] = user.as_json()
        sess['user'] = profile.as_json()
    # need to re-request '/' to re-initialize the app context
    # because the session transaction above destroys the context
    client.get('/')
    response = client.post(url_for('main.manage_connection'), data={
        'connection_id': connection.id,
        'action': 'decline',
    })
    assert response.status_code == 200
    assert connection.status == connection_status.DECLINED

def test_manage_connection_invalid_action(client):
    user = datamodels.User(
        email='user@example.com',
        id=datamodels.User.generate_uuid(),
    )
    profile = datamodels.Profile(
        display_name='User',
        handle='handle',
        user_id=user.id,
    )
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
    # need to set a user id in the session
    # this will also call socialmedia.views.auth.load_user
    with client.session_transaction() as sess:
        sess['_user_id'] = user.id
        sess['authenticated_user'] = user.as_json()
        sess['user'] = profile.as_json()
    # need to re-request '/' to re-initialize the app context
    # because the session transaction above destroys the context
    client.get('/')
    response = client.post(url_for('main.manage_connection'), data={
        'connection_id': connection.id,
        'action': 'invalid',
    })
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
    profile = datamodels.Profile(
        display_name='User',
        handle='handle',
        user_id=user.id,
    )
    with client.session_transaction() as sess:
        sess['_user_id'] = user.id
        sess['authenticated_user'] = user.as_json()
        sess['user'] = profile.as_json()
    # need to re-request '/' to re-initialize the app context
    # because the session transaction above destroys the context
    client.get('/')
    response = client.post(url_for('main.manage_connection'), data={
        'action': 'connect',
    })
    assert response.status_code == 400

def test_manage_connection_missing_connection(client):
    user = datamodels.User(
        email='user@example.com',
        id=datamodels.User.generate_uuid(),
    )
    profile = datamodels.Profile(
        display_name='User',
        handle='handle',
        user_id=user.id,
    )
    with client.session_transaction() as sess:
        sess['_user_id'] = user.id
        sess['authenticated_user'] = user.as_json()
        sess['user'] = profile.as_json()
    # need to re-request '/' to re-initialize the app context
    # because the session transaction above destroys the context
    client.get('/')
    response = client.post(url_for('main.manage_connection'), data={
        'connection_id': 'missing_connection',
        'action': 'decline',
    })
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
    message_reference_one = datamodels.MessageReference(
        connection=connection_one,
        message_id='mock_message_id',
    )
    message_reference_one.save()
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
    message_reference_two = datamodels.MessageReference(
        connection=connection_two,
        message_id='mock_message_id',
        read=True,
    )
    message_reference_two.save()
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
    with client.session_transaction() as sess:
        sess['_user_id'] = user.id
        sess['authenticated_user'] = user.as_json()
        sess['user'] = profile.as_json()
    client.get('/')
    response = client.get(url_for('main.get_connection_info'))
    assert response.status_code == 200
    json_response = json.loads(response.data)
    assert len(json_response) == 3
    assert_dict = {}
    for conn in json_response:
        assert_dict[conn['handle']] = conn

    assert assert_dict['other_handle_one']['display_name'] == connection_one.display_name
    assert assert_dict['other_handle_one']['host'] == connection_one.host
    assert assert_dict['other_handle_one']['id'] == connection_one.id
    assert assert_dict['other_handle_one']['status'] == connection_one.status
    assert assert_dict['other_handle_one']['unread_message_count'] == 1

    assert assert_dict['other_handle_two']['display_name'] == connection_two.display_name
    assert assert_dict['other_handle_two']['host'] == connection_two.host
    assert assert_dict['other_handle_two']['id'] == connection_two.id
    assert assert_dict['other_handle_two']['status'] == connection_two.status
    assert assert_dict['other_handle_two']['unread_message_count'] == 0

    assert assert_dict['requesting_user']['display_name'] == pending_connection.display_name
    assert assert_dict['requesting_user']['host'] == pending_connection.host
    assert assert_dict['requesting_user']['id'] == pending_connection.id
    assert assert_dict['requesting_user']['status'] == pending_connection.status
    assert assert_dict['requesting_user']['unread_message_count'] == 0
