import asyncio
import base64
import dateparser
import json
import requests

from collections import defaultdict
from datetime import datetime
from dateutil import tz
from flask import Blueprint, jsonify, request, url_for
from flask.json import JSONEncoder
from google.cloud import datastore
from sortedcontainers import SortedList

from socialmedia import connection_status, notification_type
from socialmedia.dataclient import datastore_client
from socialmedia.utils import generate_signed_url
from socialmedia.views.validation_decorators import (
    json_request,
    validate_request,
    validate_handle,
    validate_payload,
    validate_connection,
)
from socialmedia.views.utils import (
    decrypt_payload,
    enc_and_sign_payload,
    verify_signature,
)


blueprint = Blueprint(
    'external_comms', __name__, template_folder='templates'
)

@blueprint.route('/request-connection', methods=['POST'])
@json_request
@validate_request(fields=('enc_payload', 'handle'))
@validate_handle
def request_connection(request_data, connectee):
    ''' Requests access
        request should be JSON:
        {
          'requestor_host': 'hostname',
          'requestor_handle': 'requestor handle',
          'requestor_display_name': 'display name',
          'requestor_public_key': 'valid public key',
        }
    '''
    # because this is the first time we've talked with this user, they are unable
    # to encrypt using our public key (they don't have it yet). Instead, the
    # payload is simply base64 encoded
    try:
        request_payload = json.loads(
            base64.b64decode(request_data['enc_payload'])
        )
    except Exception:
        return 'Invalid payload - unable to convert to JSON', 400
    if not all(
        field in request_payload for field in (
            'requestor_host',
            'requestor_handle',
            'requestor_display_name',
            'requestor_public_key',
        )
    ):
        return 'Invalid request - missing required fields', 400
    ds_key = datastore_client.key('Connection', parent=connectee.key)
    connection = datastore.Entity(key=ds_key, exclude_from_indexes=('public_key',))
    now = datetime.now().astimezone(tz.UTC)
    connection.update({
        'host': request_payload['requestor_host'],
        'handle': request_payload['requestor_handle'],
        'display_name': request_payload['requestor_display_name'],
        'public_key': request_payload['requestor_public_key'],
        'status': connection_status.PENDING,
        'created': now,
        'updated': now,
    })
    datastore_client.put(connection)
    return 'Request completed', 200

@blueprint.route('/acknowledge-connection', methods=['POST'])
@json_request
@validate_request
@validate_handle
@validate_payload(
    fields=(
        'ack_host', 'ack_handle', 'ack_display_name', 'ack_public_key'
    )
)
def ack_connection(request_data, connectee, request_payload):
    ''' Endpoint to receive acknowledge connection
        request should be JSON:
        {
          'ack_host': 'acknowledger hostname',
          'ack_handle': 'acknowledger handle',
          'ack_display_name': 'acknowledger name',
          'ack_public_key': 'acknowledger public key',
        }
    '''
    query = datastore_client.query(kind='Connection')
    query.ancestor = connectee.key
    query.add_filter('handle', '=', request_payload['ack_handle'])
    query.add_filter('host', '=', request_payload['ack_host'])
    query_results = list(query.fetch(limit=1))
    if not query_results:
        return 'No connection found', 404
    connection = query_results[0]
    if connection['status'] == connection_status.CONNECTED:
        return 'Already connected', 200
    connection['public_key'] = request_payload['ack_public_key']
    now = datetime.now().astimezone(tz.UTC)
    connection.update({
        'display_name': request_payload['ack_display_name'],
        'public_key': request_payload['ack_public_key'],
        'status': connection_status.CONNECTED,
        'updated': now,
    })
    datastore_client.put(connection)
    return 'Request completed', 200

@blueprint.route('/retrieve-messages', methods=['POST'])
@json_request
@validate_request
@validate_handle
@validate_payload(fields=('host', 'handle'))
@validate_connection
def retrieve_messages(request_data, connectee, request_payload, requestor):
    ''' Requests messages for given handle
        request should be JSON:
        {
          'host': 'requestor hostname',
          'handle': 'requestor handle',
        }
        returns messages
    '''
    query = datastore_client.query(kind='Message', ancestor=connectee.key)
    messages = list(query.fetch())
    # probably could be pretty significantly optimized in some way

    commentors = defaultdict(lambda: defaultdict(set))
    messages_response = {}
    for message in messages:
        query = datastore_client.query(kind='Notification', ancestor=message.key)
        for notification in query.fetch():
           metadata = notification['metadata']
           commentors[metadata['comment_host']][metadata['comment_handle']].add(message['id'])
        if message.get('files'):
            message['files'] = [
                generate_signed_url(
                    '{}.appspot.com'.format(datastore_client.project),
                    f,
                ) for f in message['files']
            ]
        message['comments'] = SortedList(
            key=lambda x: -(dateparser.parse(x['created']).timestamp())
        )
        messages_response[message['id']] = message

    async def get_comments(host, handle, message_ids):
        request_payload = {
          'host': request.host,
          'handle': connectee['handle'],
          'message_ids': message_ids,
        }
        # user is connectee and connection is requestor
        enc_payload, enc_key, signature, nonce, tag = enc_and_sign_payload(
            connectee, requestor, request_payload
        )
        protocol = 'https'
        if host == 'localhost:8080':
            protocol = 'http'
        request_url = f'{protocol}://{host}{url_for("external_comms.retrieve_comments")}'
        payload = {
            'enc_payload': enc_payload,
            'enc_key': enc_key,
            'signature': signature,
            'nonce': nonce,
            'tag': tag,
            'handle': handle,
        }
        # send request to connection's host
        response = requests.post(
            request_url,
            json=payload,
        )
        if response.status_code == 200:
            response_data = json.loads(response.content)
            response_payload = decrypt_payload(
                connectee,
                response_data['enc_key'],
                response_data['enc_payload'],
                response_data['nonce'],
                response_data['tag'],
            )
            for comment in response_payload:
                comment['host'] = host
                comment['handle'] = handle
                messages_response[comment['message_id']]['comments'].add(comment)
        else:
            print(f'Unable to retrieve comments {response.status_code}')
            print(response.headers)
            print(response.content)

    async def collect_comments():
        gather = asyncio.gather()
        for host in commentors.keys():
            for handle, message_ids in commentors[host].items():
                asyncio.gather(get_comments(host, handle, list(message_ids)))
        await gather

    asyncio.run(collect_comments())

    def sorted_list_encoder(o):
        if isinstance(o, SortedList):
            return list(o)
        else:
            return JSONEncoder.default(None, o)

    enc_payload, enc_key, signature, nonce, tag = enc_and_sign_payload(
        connectee, requestor, messages, json_default=sorted_list_encoder
    )
    return jsonify(
        enc_payload=enc_payload,
        enc_key=enc_key,
        signature=signature,
        nonce=nonce,
        tag=tag
    ), 200


@blueprint.route('/message-notify', methods=['POST'])
@json_request
@validate_request
@validate_handle
@validate_payload(
    fields=(
        'message_host', 'message_handle', 'message_id',
    )
)
@validate_connection(host_key='message_host', handle_key='message_handle')
def message_notify(request_data, connectee, request_payload, requestor):
    ''' Notification endpoint for notification of messages from other connections
        enc_payload should be JSON:
        {
          'message_host': 'hostname',
          'message_handle': 'requestor handle',
          'message_id': 'id of new message',
        }
    '''
    ds_key = datastore_client.key('Notification', parent=requestor.key)
    notification = datastore.Entity(key=ds_key)
    now = datetime.now().astimezone(tz.UTC)
    notification.update({
        'type': notification_type.MESSAGE,
        'id': request_payload['message_id'],
        'created': now,
        'read': None,
        'metadata': {
            'message_id': request_payload['message_id'],
            'message_host': request_payload['message_host'],
            'message_handle': request_payload['message_handle'],
        }
    })
    datastore_client.put(notification)
    return '', 200

@blueprint.route('/comment-created', methods=['POST'])
@json_request
@validate_request
@validate_handle
@validate_payload(
    fields=(
        'comment_host', 'comment_handle', 'message_id', 'comment_id',
    )
)
@validate_connection(host_key='comment_host', handle_key='comment_handle')
def comment_created(request_data, connectee, request_payload, requestor):
    ''' Notification endpoint for notification of new comment on a message
        enc_payload should be JSON:
        {
          'comment_host': 'commenter hostname',
          'comment_handle': 'commenter handle',
          'message_id': 'id of message commented on',
          'comment_id': 'id of comment'
        }
    '''
    # verify signature
    if not verify_signature(requestor, request_data['signature'], request_payload):
        return 'Invalid request - signature does not match', 400
    # verify message exists
    query = datastore_client.query(kind='Message')
    query.ancestor = connectee.key
    query.add_filter('id', '=', request_payload['message_id'])
    query_results = list(query.fetch(limit=1))
    if not query_results:
        return 'No message found', 404
    message = query_results[0]
    ds_key = datastore_client.key('Notification', parent=message.key)
    notification = datastore.Entity(key=ds_key)
    now = datetime.now().astimezone(tz.UTC)
    notification.update({
        'type': notification_type.COMMENT_CREATED,
        'id': request_payload['comment_id'],
        'created': now,
        'read': True,
        'metadata': {
            'comment_host': request_payload['comment_host'],
            'comment_handle': request_payload['comment_handle']
        }
    })
    datastore_client.put(notification)
    return '', 200

@blueprint.route('/retrieve-comments', methods=['POST'])
@json_request
@validate_request
@validate_handle
@validate_payload(
    fields=(
        'host', 'handle', 'message_ids',
    )
)
@validate_connection()
def retrieve_comments(request_data, connectee, request_payload, requestor):
    ''' Requests comments for a list of messages
        enc_payload should be JSON:
        {
          'host': 'requestor host',
          'handle': 'requestor handle',
          'message_ids': ['array of message ids'],
        }
    '''
    all_comments = []
    for msg_id in request_payload['message_ids']:
        query = datastore_client.query(kind='Comment', ancestor=connectee.key)
        query.add_filter('message_id', '=', msg_id)
        all_comments.extend(list(query.fetch()))
    enc_payload, enc_key, signature, nonce, tag = enc_and_sign_payload(
        connectee, requestor, all_comments
    )
    return jsonify(
        enc_payload=enc_payload,
        enc_key=enc_key,
        signature=signature,
        nonce=nonce,
        tag=tag
    ), 200
