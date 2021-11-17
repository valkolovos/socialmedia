import base64
import json
import os
from datetime import datetime

import requests

from dateutil import tz
from flask import Blueprint, request, url_for
from google.cloud import datastore

from socialmedia import connection_status
from socialmedia.dataclient import datastore_client
from socialmedia.utils import TaskManager
from socialmedia.views.validation_decorators import (
    json_request,
    validate_request,
)
from socialmedia.views.utils import enc_and_sign_payload

blueprint = Blueprint('queue_workers', __name__)

task_manager = TaskManager(
    datastore_client.project, 'us-west2',
    os.environ.get('ASYNC_TASKS', 'true').lower() == 'true'
)

@blueprint.route('/ack-connection', methods=['POST'])
@json_request
@validate_request(fields=(
    'user_key', 'connection_id',
))
def ack_connection(request_data):
    '''
        payload = {
            'user_host': 'acknowledging user host',
            'user_key': user_id,
            'connection_id': connection_id
        }
    '''
    user_key = datastore_client.key('Profile', request_data['user_key'])
    user = datastore_client.get(user_key)
    connection_key = datastore_client.key(
        'Profile', user.id, 'Connection', request_data['connection_id']
    )
    connection = datastore_client.get(connection_key)
    if not connection:
        return 404, 'No connection {} found for user {}'.format(
                request_data['connection_id'], user['display_name']
            )
    request_payload = {
      'ack_host': request_data['user_host'],
      'ack_handle': user['handle'],
      'ack_display_name': user['display_name'],
      'ack_public_key': user['public_key'].decode(),
    }
    enc_payload, enc_key, signature, nonce, tag = enc_and_sign_payload(
        user, connection, request_payload
    )
    protocol = 'https'
    if connection['host'] == 'localhost:8080':
        protocol = 'http'
    request_url = f'{protocol}://{connection["host"]}{url_for("external_comms.ack_connection")}'
    # send request to connection's host
    response = requests.post(
        request_url,
        json={
            'enc_payload': enc_payload,
            'enc_key': enc_key,
            'signature': signature,
            'nonce': nonce,
            'tag': tag,
            'handle': connection['handle'],
        }
    )
    if response.status_code == 200:
        connection.update({
            'status': connection_status.CONNECTED,
            'updated': datetime.now().astimezone(tz.UTC),
        })
        datastore_client.put(connection)
    return 'Connection requested', 200

@blueprint.route('/request-connection', methods=['POST'])
@json_request
@validate_request(fields=(
    'user_key', 'host', 'handle'
))
def request_connection(request_data):
    ''' Requests a connection with another user
        payload should be JSON
        {
            'request_host': 'host of requesting user',
            'user_key': 'user key for datastore (profile id)',
            'host': 'host where connection lives',
            'handle': 'handle of connection'
        }
    '''
    user_key = datastore_client.key('Profile', request_data['user_key'])
    # get full user from datastore
    user = datastore_client.get(user_key)
    request_payload = {
      'requestor_host': request_data['user_host'],
      'requestor_handle': user['handle'],
      'requestor_display_name': user['display_name'],
      'requestor_public_key': user['public_key'].decode(),
    }
    protocol = 'https'
    if request_data['host'] == 'localhost:8080':
        protocol = 'http'
    request_url = f'{protocol}://{request_data["host"]}{url_for("external_comms.request_connection")}'
    # send request to connection's host
    response = requests.post(
        request_url, json={
            'enc_payload': base64.b64encode(
                json.dumps(request_payload).encode()
            ).decode(),
            'handle': request_data['handle'],
        }
    )
    if response.status_code == 200:
        # store pending connection - the rest of the connection will get populated
        # when the acknowledgement comes back
        ds_key = datastore_client.key('Connection', parent=user.key)
        connection = datastore.Entity(key=ds_key, exclude_from_indexes=('public_key', ))
        now = datetime.now().astimezone(tz.UTC)
        connection.update({
            'host': request_data['host'],
            'handle': request_data['handle'],
            'status': connection_status.REQUESTED,
            'created': now,
            'updated': now,
        })
        datastore_client.put(connection)
    else:
        print('QueueWorker: requestConnection failed - {}'.format(
            response.content
        ))
        return 'Connection request failed', response.status_code
    return 'Connection requested', 200

@blueprint.route('/message-created', methods=['POST'])
@json_request
@validate_request(fields=('message_id',))
def message_created(request_data):
    ''' Finds all connections and puts a task on the message-notify queue
        for each to notify that a new message has been created
        payload should be JSON
        {
            'message_id': 'message id'
        }
    '''
    query = datastore_client.query(kind='Message')
    query.add_filter('id', '=', request_data['message_id'])
    messages = list(query.fetch(limit=1))
    if messages:
        query = datastore_client.query(kind='Connection', ancestor=messages[0].key.parent)
        query.add_filter('status', '=', connection_status.CONNECTED)
        for connection in query.fetch():
            payload = {
                'user_key': messages[0].key.parent.id,
                'message_id': request_data['message_id'],
                'connection_key': connection.id,
            }
            task_manager.queue_task(
                payload,
                'message-notify',
                url_for('queue_workers.message_notify')
            )
    return 'Notification tasks created', 200

@blueprint.route('/message-notify', methods=['POST'])
@json_request
@validate_request(fields=(
    'user_key',
    'message_id',
    'connection_key'
))
def message_notify(request_data):
    '''
        Notifies a connection that a new message has been posted
        payload should be JSON
        {
            'user_key': 'user key for datastore', # message creator
            'message_id': 'message id'
            'connection_key': 'connection key', # connection to notify
        }
    '''
    user_key = datastore_client.key('Profile', request_data['user_key'])
    # get full user from datastore
    user = datastore_client.get(user_key)
    connection_key = datastore_client.key(
        'Connection',
        request_data['connection_key'],
        parent=user_key
    )
    connection = datastore_client.get(connection_key)
    request_payload = {
      'message_host': request.host,
      'message_handle': user['handle'],
      'message_id': request_data['message_id'],
    }
    enc_payload, enc_key, signature, nonce, tag = enc_and_sign_payload(
        user, connection, request_payload
    )
    protocol = 'https'
    if connection['host'] == 'localhost:8080':
        protocol = 'http'
    request_url = f'{protocol}://{connection["host"]}{url_for("external_comms.message_notify")}'
    # send request to connection's host
    response = requests.post(
        request_url,
        json={
            'enc_payload': enc_payload,
            'enc_key': enc_key,
            'signature': signature,
            'nonce': nonce,
            'tag': tag,
            'handle': connection['handle'],
        }
    )
    if response.status_code != 200:
        print('Message notify failed {}:{}'.format(response.status_code, response.content))
        return (
            'Message notify failed {}:{}'.format(response.status_code, response.content),
            response.status_code
        )
    return 'Connection {}@{} notified'.format(connection['handle'], connection['host']), 200

@blueprint.route('/comment-created', methods=['POST'])
@json_request
@validate_request(fields=(
    'user_key',
    'user_host',
    'message_id',
    'comment_id',
    'connection_key',
))
def comment_created(request_data):
    ''' Notifies a connection that a comment has been added to their message
        payload should be JSON
        {
            'user_key': 'user key for datastore', # message creator
            'user_host': 'users host',
            'message_id': 'message id'
            'comment_id': 'comment id in datastore',
            'connection_key': 'connection key', # connection to notify
        }
    '''
    user_key = datastore_client.key('Profile', request_data['user_key'])
    # get full user from datastore
    user = datastore_client.get(user_key)
    connection_key = datastore_client.key('Connection', request_data['connection_key'], parent=user_key)
    connection = datastore_client.get(connection_key)
    request_payload = {
      'comment_host': request_data['user_host'],
      'comment_handle': user['handle'],
      'message_id': request_data['message_id'],
      'comment_id': request_data['comment_id'],
    }
    enc_payload, enc_key, signature, nonce, tag = enc_and_sign_payload(
        user, connection, request_payload
    )
    protocol = 'https'
    if connection['host'] == 'localhost:8080':
        protocol = 'http'
    request_url = f'{protocol}://{connection["host"]}{url_for("external_comms.comment_created")}'
    # send request to connection's host
    response = requests.post(
        request_url,
        json={
            'enc_payload': enc_payload,
            'enc_key': enc_key,
            'signature': signature,
            'nonce': nonce,
            'tag': tag,
            'handle': connection['handle'],
        }
    )
    if response.status_code != 200:
        print('New comment notify failed {}:{}'.format(response.status_code, response.content))
        return (
            'New comment notify failed {}:{}'.format(response.status_code, response.content),
            response.status_code
        )
    return 'Connection {}@{} notified of comment {} on message {}'.format(
        connection['handle'],
        connection['host'],
        request_data['message_id'],
        request_data['comment_id']
    ), 200
