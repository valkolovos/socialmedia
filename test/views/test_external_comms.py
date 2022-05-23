import base64
import json

from collections import namedtuple
from datetime import datetime, timedelta
from dateutil import tz
from flask import url_for
from unittest import mock
from uuid import UUID

from socialmedia import connection_status
from socialmedia.views.utils import enc_and_sign_payload, decrypt_payload
from test import datamodels
from .utils import client

MockResponse = namedtuple('NamedResponse', ['status_code', 'content', 'headers'])

def test_request_connection(client):
    requestor_user = datamodels.User(
        email='requestor@example.com',
        id=datamodels.User.generate_uuid(),
    )
    requestor_profile = datamodels.Profile(
        display_name='Requestor User',
        handle='requestor_handle',
        user_id=requestor_user.id,
    )
    requested_user = datamodels.User(
        email='other_user@testhost.com',
        id=datamodels.User.generate_uuid(),
    )
    requested_user.save()
    requested_profile = datamodels.Profile(
        display_name='Other User',
        handle='other_user',
        user_id=requested_user.id,
    )
    requested_profile.save()
    request_payload = {
      'requestor_host': 'localhost',
      'requestor_handle': requestor_profile.handle,
      'requestor_display_name': requestor_profile.display_name,
      'requestor_public_key': str(requestor_profile.public_key),
    }
    response = client.post(url_for('external_comms.request_connection'), json={
        'enc_payload': base64.b64encode(
            json.dumps(request_payload).encode()
        ).decode(),
        'handle': requested_profile.handle
    })
    assert response.status_code == 200
    connectee_connection = datamodels.Connection.get(handle=requestor_profile.handle)
    assert connectee_connection.host == 'localhost'
    assert connectee_connection.display_name == requestor_profile.display_name
    assert connectee_connection.public_key == str(requestor_profile.public_key)
    assert connectee_connection.status == connection_status.PENDING
    assert UUID(connectee_connection.id, version=4) is not None
    assert connectee_connection.profile == requested_profile

def test_request_connection_invalid_payload(client):
    requestor_user = datamodels.User(
        email='requestor@example.com',
        id=datamodels.User.generate_uuid(),
    )
    requestor_profile = datamodels.Profile(
        display_name='Requestor User',
        handle='requestor_handle',
        user_id=requestor_user.id,
    )
    requested_user = datamodels.User(
        email='other_user@testhost.com',
        id=datamodels.User.generate_uuid(),
    )
    requested_user.save()
    requested_profile = datamodels.Profile(
        display_name='Other User',
        handle='other_user',
        user_id=requested_user.id,
    )
    requested_profile.save()
    response = client.post(url_for('external_comms.request_connection'), json={
        'enc_payload': 'this should not work',
        'handle': requested_profile.handle
    })
    assert response.status_code == 400
    assert response.data == b'Invalid payload - unable to convert to JSON'

def test_request_connection_invalid_request(client):
    requestor_user = datamodels.User(
        email='requestor@example.com',
        id=datamodels.User.generate_uuid(),
    )
    requestor_profile = datamodels.Profile(
        display_name='Requestor User',
        handle='requestor_handle',
        user_id=requestor_user.id,
    )
    requested_user = datamodels.User(
        email='other_user@testhost.com',
        id=datamodels.User.generate_uuid(),
    )
    requested_user.save()
    requested_profile = datamodels.Profile(
        display_name='Other User',
        handle='other_user',
        user_id=requested_user.id,
    )
    requested_profile.save()
    # missing required 'requestor_public_key'
    request_payload = {
      'requestor_host': 'localhost',
      'requestor_handle': requestor_profile.handle,
      'requestor_display_name': requestor_profile.display_name,
    }
    response = client.post(url_for('external_comms.request_connection'), json={
        'enc_payload': base64.b64encode(
            json.dumps(request_payload).encode()
        ).decode(),
        'handle': requested_profile.handle
    })
    assert response.status_code == 400
    assert response.data == b'Invalid request - missing required fields'

def test_ack_connection(client):
    requestor_user = datamodels.User(
        email='requestor@example.com',
        id=datamodels.User.generate_uuid(),
    )
    requestor_profile = datamodels.Profile(
        display_name='Requestor User',
        handle='requestor_handle',
        user_id=requestor_user.id,
    )

    requested_user = datamodels.User(
        email='other_user@testhost.com',
        id=datamodels.User.generate_uuid(),
    )
    requested_user.save()
    requested_profile = datamodels.Profile(
        display_name='Other User',
        handle='other_user',
        user_id=requested_user.id,
    )
    requested_profile.save()
    requestor_connection = datamodels.Connection(
        profile=requestor_profile,
        host='https://other_host.com',
        handle=requested_profile.handle,
        display_name=requested_profile.display_name,
        public_key=requested_profile.public_key,
        status=connection_status.PENDING,
    )
    dt = (datetime.now() - timedelta(days=1)).astimezone(tz.UTC)
    requested_connection = datamodels.Connection(
        handle=requestor_profile.handle,
        host='localhost',
        display_name=requestor_profile.handle,
        public_key=requestor_profile.public_key,
        status=connection_status.PENDING,
        profile=requested_profile,
        created=dt,
        updated=dt
    )
    requested_connection.save()

    request_payload = {
      'ack_host': 'localhost',
      'ack_handle': requestor_profile.handle,
      'ack_display_name': requestor_profile.display_name,
      'ack_public_key': requestor_profile.public_key.decode(),
    }
    enc_payload, enc_key, signature, nonce, tag = enc_and_sign_payload(
        requestor_profile, requestor_connection, request_payload
    )
    # send request to connection's host
    response = client.post(
        url_for("external_comms.ack_connection"),
        json={
            'enc_payload': enc_payload,
            'enc_key': enc_key,
            'signature': signature,
            'nonce': nonce,
            'tag': tag,
            'handle': requestor_connection.handle,
        }
    )
    assert response.status_code == 200
    assert requested_connection.status == connection_status.CONNECTED
    assert requested_connection.updated > requested_connection.created

def test_ack_connection_doesnt_exist(client):
    requestor_user = datamodels.User(
        email='requestor@example.com',
        id=datamodels.User.generate_uuid(),
    )
    requestor_profile = datamodels.Profile(
        display_name='Requestor User',
        handle='requestor_handle',
        user_id=requestor_user.id,
    )

    requested_user = datamodels.User(
        email='other_user@testhost.com',
        id=datamodels.User.generate_uuid(),
    )
    requested_user.save()
    requested_profile = datamodels.Profile(
        display_name='Other User',
        handle='other_user',
        user_id=requested_user.id,
    )
    requested_profile.save()
    requestor_connection = datamodels.Connection(
        profile=requestor_profile,
        host='https://other_host.com',
        handle=requested_profile.handle,
        display_name=requested_profile.display_name,
        public_key=requested_profile.public_key,
        status=connection_status.PENDING,
    )

    request_payload = {
      'ack_host': 'localhost',
      'ack_handle': requestor_profile.handle,
      'ack_display_name': requestor_profile.display_name,
      'ack_public_key': requestor_profile.public_key.decode(),
    }
    enc_payload, enc_key, signature, nonce, tag = enc_and_sign_payload(
        requestor_profile, requestor_connection, request_payload
    )
    # send request to connection's host
    response = client.post(
        url_for("external_comms.ack_connection"),
        json={
            'enc_payload': enc_payload,
            'enc_key': enc_key,
            'signature': signature,
            'nonce': nonce,
            'tag': tag,
            'handle': requestor_connection.handle,
        }
    )
    assert response.status_code == 404

def test_ack_connection_already_connected(client):
    requestor_user = datamodels.User(
        email='requestor@example.com',
        id=datamodels.User.generate_uuid(),
    )
    requestor_profile = datamodels.Profile(
        display_name='Requestor User',
        handle='requestor_handle',
        user_id=requestor_user.id,
    )

    requested_user = datamodels.User(
        email='other_user@testhost.com',
        id=datamodels.User.generate_uuid(),
    )
    requested_user.save()
    requested_profile = datamodels.Profile(
        display_name='Other User',
        handle='other_user',
        user_id=requested_user.id,
    )
    requested_profile.save()
    requestor_connection = datamodels.Connection(
        profile=requestor_profile,
        host='https://other_host.com',
        handle=requested_profile.handle,
        display_name=requested_profile.display_name,
        public_key=requested_profile.public_key,
        status=connection_status.PENDING,
    )
    dt = (datetime.now() - timedelta(days=1)).astimezone(tz.UTC)
    requested_connection = datamodels.Connection(
        handle=requestor_profile.handle,
        host='localhost',
        display_name=requestor_profile.handle,
        public_key=requestor_profile.public_key,
        status=connection_status.CONNECTED,
        profile=requested_profile,
        created=dt,
        updated=dt
    )
    requested_connection.save()

    request_payload = {
      'ack_host': 'localhost',
      'ack_handle': requestor_profile.handle,
      'ack_display_name': requestor_profile.display_name,
      'ack_public_key': requestor_profile.public_key.decode(),
    }
    enc_payload, enc_key, signature, nonce, tag = enc_and_sign_payload(
        requestor_profile, requestor_connection, request_payload
    )
    # send request to connection's host
    response = client.post(
        url_for("external_comms.ack_connection"),
        json={
            'enc_payload': enc_payload,
            'enc_key': enc_key,
            'signature': signature,
            'nonce': nonce,
            'tag': tag,
            'handle': requestor_connection.handle,
        }
    )
    assert response.status_code == 200
    assert requested_connection.updated == requested_connection.created

def test_retrieve_messages(client):
    requestor_user = datamodels.User(
        email='requestor@example.com',
        id=datamodels.User.generate_uuid(),
    )
    requestor_profile = datamodels.Profile(
        display_name='Requestor User',
        handle='requestor_handle',
        user_id=requestor_user.id,
    )

    requested_user = datamodels.User(
        email='requestee@testhost.com',
        id=datamodels.User.generate_uuid(),
    )
    requested_user.save()
    requested_profile = datamodels.Profile(
        display_name='Requestee',
        handle='requestee',
        user_id=requested_user.id,
    )
    requested_profile.save()

    third_profile = datamodels.Profile(
        display_name='Third Connection',
        handle='third_connection',
        user_id=datamodels.User(
            email='a@b.c', id=datamodels.User.generate_uuid()
        ).id
    )
    requestor_connection = datamodels.Connection(
        profile=requestor_profile,
        host='https://other_host.com',
        handle=requested_profile.handle,
        display_name=requested_profile.display_name,
        public_key=requested_profile.public_key,
        status=connection_status.CONNECTED,
    )
    requested_connection = datamodels.Connection(
        handle=requestor_profile.handle,
        host='localhost',
        display_name=requestor_profile.handle,
        public_key=requestor_profile.public_key,
        status=connection_status.CONNECTED,
        profile=requested_profile,
    )
    requested_connection.save()
    third_connection = datamodels.Connection(
        handle=third_profile.handle,
        host='localhost',
        display_name=third_profile.display_name,
        public_key=third_profile.public_key,
        status=connection_status.CONNECTED,
        profile=requested_profile,
    )
    third_connection.save()
    message_one = datamodels.Message(
        profile=requested_profile,
        text='This is a message',
        files=['message_one.png'],
    )
    message_one.save()
    message_two = datamodels.Message(
        profile=requested_profile,
        text='This is a message without comments or files',
    )
    message_two.save()
    message_three = datamodels.Message(
        profile=requested_profile,
        text='This is a message with one comment and no files',
    )
    message_three.save()
    comment_one_reference = datamodels.CommentReference(
        connection=requested_connection,
        message_id=message_one.id,
    )
    comment_one_reference.save()
    comment_two_reference = datamodels.CommentReference(
        connection=third_connection,
        message_id=message_one.id,
    )
    comment_two_reference.save()
    comment_three_reference = datamodels.CommentReference(
        connection=third_connection,
        message_id=message_three.id,
    )
    comment_three_reference.save()

    request_payload = {
        'host': requested_connection.host,
        'handle': requested_connection.handle
    }
    enc_payload, enc_key, signature, nonce, tag = enc_and_sign_payload(
        requestor_profile, requestor_connection, request_payload
    )
    # send request to connection's host
    with mock.patch('socialmedia.views.utils.requests') as req:
        def side_effect(*args, **kwargs):
            json_payload = kwargs['json']
            if json_payload['handle'] == requestor_profile.handle:
                comment = datamodels.Comment(
                    profile=requestor_profile,
                    message_id=message_one.id,
                    text='This is a comment from requestor',
                    files=['file1.png']
                )
                enc_payload, enc_key, signature, nonce, tag = enc_and_sign_payload(
                    requestor_profile, requested_profile, [comment.as_json()]
                )
                return MockResponse(200, json.dumps({
                    'enc_payload': enc_payload,
                    'enc_key': enc_key,
                    'signature': signature,
                    'nonce': nonce,
                    'tag': tag
                }), None)
            elif json_payload['handle'] == third_connection.handle:
                request_payload = decrypt_payload(
                    third_profile,
                    json_payload['enc_key'],
                    json_payload['enc_payload'],
                    json_payload['nonce'],
                    json_payload['tag'],
                )
                comments = []
                for message_id in request_payload['message_ids']:
                    if message_id == message_one.id:
                        comments.append(datamodels.Comment(
                            profile=third_profile,
                            message_id=message_one.id,
                            text='This is a comment from third_profile'
                        ))
                    elif message_id == message_three.id:
                        comments.append(datamodels.Comment(
                            profile=third_profile,
                            message_id=message_three.id,
                            text='This is a comment on message_three from third_profile'
                        ))
                enc_payload, enc_key, signature, nonce, tag = enc_and_sign_payload(
                    third_profile, requested_profile, [comment.as_json() for comment in comments]
                )
                return MockResponse(200, json.dumps({
                    'enc_payload': enc_payload,
                    'enc_key': enc_key,
                    'signature': signature,
                    'nonce': nonce,
                    'tag': tag
                }), None)
        req.post.side_effect = side_effect
        response = client.post(
            url_for("external_comms.retrieve_messages"),
            json={
                'enc_payload': enc_payload,
                'enc_key': enc_key,
                'signature': signature,
                'nonce': nonce,
                'tag': tag,
                'handle': requestor_connection.handle,
            }
        )
        assert response.status_code == 200
        request_data = json.loads(response.data)
        request_payload = decrypt_payload(
            requestor_profile,
            request_data['enc_key'],
            request_data['enc_payload'],
            request_data['nonce'],
            request_data['tag'],
        )
        assert len(request_payload) == 3
        response_message = request_payload[0]
        assert len(response_message['comments']) == 2
        assert response_message['id'] == message_one.id
        assert response_message['text'] == message_one.text
        assert len(response_message['files']) == 1
        assert response_message['files'][0] == 'test_message_one.png'
        requestor_comment = third_person_comment = None
        for comment in response_message['comments']:
            if comment['profile']['handle'] == requestor_profile.handle:
                requestor_comment = comment
            elif comment['profile']['handle'] == third_profile.handle:
                third_person_comment = comment
        assert requestor_comment['text'] == 'This is a comment from requestor'
        assert len(requestor_comment['files']) == 1
        assert requestor_comment['files'][0] == 'file1.png'
        assert requestor_comment['message_id'] == message_one.id
        assert third_person_comment['text'] == 'This is a comment from third_profile'
        assert not third_person_comment['files']
        assert third_person_comment['message_id'] == message_one.id
        response_message_two = request_payload[1]
        assert len(response_message_two['comments']) == 0
        assert len(response_message_two['files']) == 0
        assert response_message_two['text'] == message_two.text
        response_message_three = request_payload[2]

def test_retrieve_messages_failed_comment_retrieval(client):
    # request to get comments fails, but messages are still returned
    requestor_user = datamodels.User(
        email='requestor@example.com',
        id=datamodels.User.generate_uuid(),
    )
    requestor_profile = datamodels.Profile(
        display_name='Requestor User',
        handle='requestor_handle',
        user_id=requestor_user.id,
    )

    requested_user = datamodels.User(
        email='requestee@testhost.com',
        id=datamodels.User.generate_uuid(),
    )
    requested_user.save()
    requested_profile = datamodels.Profile(
        display_name='Requestee',
        handle='requestee',
        user_id=requested_user.id,
    )
    requested_profile.save()

    third_profile = datamodels.Profile(
        display_name='Third Connection',
        handle='third_connection',
        user_id=datamodels.User(
            email='a@b.c', id=datamodels.User.generate_uuid()
        ).id
    )
    requestor_connection = datamodels.Connection(
        profile=requestor_profile,
        host='https://other_host.com',
        handle=requested_profile.handle,
        display_name=requested_profile.display_name,
        public_key=requested_profile.public_key,
        status=connection_status.CONNECTED,
    )
    requested_connection = datamodels.Connection(
        handle=requestor_profile.handle,
        host='localhost',
        display_name=requestor_profile.handle,
        public_key=requestor_profile.public_key,
        status=connection_status.CONNECTED,
        profile=requested_profile,
    )
    requested_connection.save()
    third_connection = datamodels.Connection(
        handle=third_profile.handle,
        host='localhost',
        display_name=third_profile.display_name,
        public_key=third_profile.public_key,
        status=connection_status.CONNECTED,
        profile=requested_profile,
    )
    third_connection.save()
    message_one = datamodels.Message(
        profile=requested_profile,
        text='This is a message',
        files=['message_one.png'],
    )
    message_one.save()
    message_two = datamodels.Message(
        profile=requested_profile,
        text='This is a message without comments or files',
    )
    message_two.save()
    comment_one_reference = datamodels.CommentReference(
        connection=requested_connection,
        message_id=message_one.id,
    )
    comment_one_reference.save()
    comment_two_reference = datamodels.CommentReference(
        connection=third_connection,
        message_id=message_one.id,
    )
    comment_two_reference.save()

    request_payload = {
        'host': requested_connection.host,
        'handle': requested_connection.handle
    }
    enc_payload, enc_key, signature, nonce, tag = enc_and_sign_payload(
        requestor_profile, requestor_connection, request_payload
    )
    # send request to connection's host
    with mock.patch('socialmedia.views.utils.requests') as req:
        def side_effect(*args, **kwargs):
            json_payload = kwargs['json']
            if json_payload['handle'] == requestor_profile.handle:
                comment = datamodels.Comment(
                    profile=requestor_profile,
                    message_id=message_one.id,
                    text='This is a comment from requestor',
                    files=['file1.png'],
                    created=datetime.now() - timedelta(days=1),
                )
                enc_payload, enc_key, signature, nonce, tag = enc_and_sign_payload(
                    requestor_profile, requested_profile, [comment.as_json()]
                )
                return MockResponse(200, json.dumps({
                    'enc_payload': enc_payload,
                    'enc_key': enc_key,
                    'signature': signature,
                    'nonce': nonce,
                    'tag': tag
                }), None)
            elif json_payload['handle'] == third_connection.handle:
                return MockResponse(500, 'Fake comment retrival server error', None)
        req.post.side_effect = side_effect
        response = client.post(
            url_for("external_comms.retrieve_messages"),
            json={
                'enc_payload': enc_payload,
                'enc_key': enc_key,
                'signature': signature,
                'nonce': nonce,
                'tag': tag,
                'handle': requestor_connection.handle,
            }
        )
        assert response.status_code == 200
        request_data = json.loads(response.data)
        request_payload = decrypt_payload(
            requestor_profile,
            request_data['enc_key'],
            request_data['enc_payload'],
            request_data['nonce'],
            request_data['tag'],
        )
        assert len(request_payload) == 2
        response_message = request_payload[0]
        assert len(response_message['comments']) == 2
        assert response_message['id'] == message_one.id
        assert response_message['text'] == message_one.text
        assert len(response_message['files']) == 1
        assert response_message['files'][0] == 'test_message_one.png'
        third_person_comment = None
        for comment in response_message['comments']:
            if comment['profile']['handle'] == third_profile.handle:
                third_person_comment = comment
        assert third_person_comment['text'] == 'error retrieving comments'
        assert third_person_comment['files'] == []


def test_message_notify(client):
    requestor_user = datamodels.User(
        email='requestor@example.com',
        id=datamodels.User.generate_uuid(),
    )
    requestor_profile = datamodels.Profile(
        display_name='Requestor User',
        handle='requestor_handle',
        user_id=requestor_user.id,
    )

    requested_user = datamodels.User(
        email='requestee@testhost.com',
        id=datamodels.User.generate_uuid(),
    )
    requested_user.save()
    requested_profile = datamodels.Profile(
        display_name='Requestee',
        handle='requestee',
        user_id=requested_user.id,
    )
    requested_profile.save()
    requestor_connection = datamodels.Connection(
        profile=requestor_profile,
        host='https://other_host.com',
        handle=requested_profile.handle,
        display_name=requested_profile.display_name,
        public_key=requested_profile.public_key,
        status=connection_status.CONNECTED,
    )
    requested_connection = datamodels.Connection(
        handle=requestor_profile.handle,
        host='localhost',
        display_name=requestor_profile.handle,
        public_key=requestor_profile.public_key,
        status=connection_status.CONNECTED,
        profile=requested_profile,
    )
    requested_connection.save()

    request_payload = {
      'message_host': 'localhost',
      'message_handle': requestor_profile.handle,
      'message_id': 'mock_message_id',
    }
    enc_payload, enc_key, signature, nonce, tag = enc_and_sign_payload(
        requestor_profile, requestor_connection, request_payload
    )
    # send request to connection's host
    response = client.post(
        url_for("external_comms.message_notify"),
        json={
            'enc_payload': enc_payload,
            'enc_key': enc_key,
            'signature': signature,
            'nonce': nonce,
            'tag': tag,
            'handle': requestor_connection.handle,
        }
    )
    assert response.status_code == 200
    message_reference =  datamodels.MessageReference.get(message_id='mock_message_id')
    assert message_reference.connection == requested_connection
    assert message_reference.read is None

def test_comment_created(client):
    requestor_user = datamodels.User(
        email='requestor@example.com',
        id=datamodels.User.generate_uuid(),
    )
    requestor_profile = datamodels.Profile(
        display_name='Requestor User',
        handle='requestor_handle',
        user_id=requestor_user.id,
    )

    requested_user = datamodels.User(
        email='requestee@testhost.com',
        id=datamodels.User.generate_uuid(),
    )
    requested_user.save()
    requested_profile = datamodels.Profile(
        display_name='Requestee',
        handle='requestee',
        user_id=requested_user.id,
    )
    requested_profile.save()
    requestor_connection = datamodels.Connection(
        profile=requestor_profile,
        host='https://other_host.com',
        handle=requested_profile.handle,
        display_name=requested_profile.display_name,
        public_key=requested_profile.public_key,
        status=connection_status.CONNECTED,
    )
    requested_connection = datamodels.Connection(
        handle=requestor_profile.handle,
        host='localhost',
        display_name=requestor_profile.handle,
        public_key=requestor_profile.public_key,
        status=connection_status.CONNECTED,
        profile=requested_profile,
    )
    requested_connection.save()
    # nothing except the id gets looked at, so not
    # bothering to fully populate
    message = datamodels.Message()
    message.save()
    comment = datamodels.Comment(message_id=message.id)
    comment.save()
    request_payload = {
      'comment_host': requested_connection.host,
      'comment_handle': requested_connection.handle,
      'message_id': message.id,
      'comment_id': comment.id,
    }
    enc_payload, enc_key, signature, nonce, tag = enc_and_sign_payload(
        requestor_profile, requestor_connection, request_payload
    )
    # send request to connection's host
    response = client.post(
        url_for("external_comms.comment_created"),
        json={
            'enc_payload': enc_payload,
            'enc_key': enc_key,
            'signature': signature,
            'nonce': nonce,
            'tag': tag,
            'handle': requestor_connection.handle,
        }
    )
    assert response.status_code == 200
    comment_reference = datamodels.CommentReference.get()
    assert comment_reference is not None
    assert comment_reference.connection == requested_connection
    assert comment_reference.message_id == message.id

def test_comment_created_no_message(client):
    requestor_user = datamodels.User(
        email='requestor@example.com',
        id=datamodels.User.generate_uuid(),
    )
    requestor_profile = datamodels.Profile(
        display_name='Requestor User',
        handle='requestor_handle',
        user_id=requestor_user.id,
    )

    requested_user = datamodels.User(
        email='requestee@testhost.com',
        id=datamodels.User.generate_uuid(),
    )
    requested_user.save()
    requested_profile = datamodels.Profile(
        display_name='Requestee',
        handle='requestee',
        user_id=requested_user.id,
    )
    requested_profile.save()
    requestor_connection = datamodels.Connection(
        profile=requestor_profile,
        host='https://other_host.com',
        handle=requested_profile.handle,
        display_name=requested_profile.display_name,
        public_key=requested_profile.public_key,
        status=connection_status.CONNECTED,
    )
    requested_connection = datamodels.Connection(
        handle=requestor_profile.handle,
        host='localhost',
        display_name=requestor_profile.handle,
        public_key=requestor_profile.public_key,
        status=connection_status.CONNECTED,
        profile=requested_profile,
    )
    requested_connection.save()
    message_id = datamodels.Message.generate_uuid()
    request_payload = {
      'comment_host': requested_connection.host,
      'comment_handle': requested_connection.handle,
      'message_id': message_id,
      'comment_id': datamodels.Comment.generate_uuid()
    }
    enc_payload, enc_key, signature, nonce, tag = enc_and_sign_payload(
        requestor_profile, requestor_connection, request_payload
    )
    # send request to connection's host
    response = client.post(
        url_for("external_comms.comment_created"),
        json={
            'enc_payload': enc_payload,
            'enc_key': enc_key,
            'signature': signature,
            'nonce': nonce,
            'tag': tag,
            'handle': requestor_connection.handle,
        }
    )
    assert response.status_code == 404
    assert response.data == bytes(f'No message found for id {message_id}', 'utf-8')
    assert datamodels.CommentReference.get() is None

def test_retrieve_comments(client):
    requestor_user = datamodels.User(
        email='requestor@example.com',
        id=datamodels.User.generate_uuid(),
    )
    requestor_profile = datamodels.Profile(
        display_name='Requestor User',
        handle='requestor_handle',
        user_id=requestor_user.id,
    )

    requested_user = datamodels.User(
        email='requestee@testhost.com',
        id=datamodels.User.generate_uuid(),
    )
    requested_user.save()
    requested_profile = datamodels.Profile(
        display_name='Requestee',
        handle='requestee',
        user_id=requested_user.id,
    )
    requested_profile.save()
    requestor_connection = datamodels.Connection(
        profile=requestor_profile,
        host='https://other_host.com',
        handle=requested_profile.handle,
        display_name=requested_profile.display_name,
        public_key=requested_profile.public_key,
        status=connection_status.CONNECTED,
    )
    requested_connection = datamodels.Connection(
        handle=requestor_profile.handle,
        host='localhost',
        display_name=requestor_profile.handle,
        public_key=requestor_profile.public_key,
        status=connection_status.CONNECTED,
        profile=requested_profile,
    )
    requested_connection.save()
    message_ids = ['message_1', 'message_2']
    for i in range(5):
        comment = datamodels.Comment(
            profile=requested_profile,
            message_id=message_ids[0],
            text=f'This is comment number {i+1}',
            files=[f'file-{i+1}.txt']
        )
        comment.save()
    for i in range(5,10):
        comment = datamodels.Comment(
            profile=requested_profile,
            message_id=message_ids[1],
            text=f'This is comment number {i+1}',
            files=[f'file-{i+1}.txt']
        )
        comment.save()
    request_payload = {
      'host': 'localhost',
      'handle': requestor_profile.handle,
      'message_ids': message_ids,
    }
    enc_payload, enc_key, signature, nonce, tag = enc_and_sign_payload(
        requestor_profile, requestor_connection, request_payload
    )
    # send request to connection's host
    response = client.post(
        url_for("external_comms.retrieve_comments"),
        json={
            'enc_payload': enc_payload,
            'enc_key': enc_key,
            'signature': signature,
            'nonce': nonce,
            'tag': tag,
            'handle': requestor_connection.handle,
        }
    )
    assert response.status_code == 200
    request_data = json.loads(response.data)
    request_payload = decrypt_payload(
        requestor_profile,
        request_data['enc_key'],
        request_data['enc_payload'],
        request_data['nonce'],
        request_data['tag'],
    )
    assert len(request_payload) == 10
    assert any(comment['text'] == 'This is comment number 1' for comment in request_payload)
    assert any(comment['text'] == 'This is comment number 6' for comment in request_payload)
    assert all(comment['profile']['handle'] == 'requestee' for comment in request_payload)
    assert sum(comment['message_id'] == message_ids[0] for comment in request_payload) == 5
    assert sum(comment['message_id'] == message_ids[1] for comment in request_payload) == 5
