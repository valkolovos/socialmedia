import asyncio
import base64
import dateparser
import json
import requests

from collections import defaultdict
from datetime import datetime
from dateutil import tz
from flask import Blueprint, current_app, jsonify, request, url_for
from flask.json import JSONEncoder
from sortedcontainers import SortedList

from socialmedia import connection_status
from socialmedia.utils import generate_signed_urls
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
    connection = current_app.datamodels.Connection(
        profile=connectee,
        host=request_payload['requestor_host'],
        handle=request_payload['requestor_handle'],
        display_name=request_payload['requestor_display_name'],
        public_key=request_payload['requestor_public_key'],
        status=connection_status.PENDING,
    )
    connection.save()
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
    connection = current_app.datamodels.Connection.get(
        handle = request_payload['ack_handle'],
        host = request_payload['ack_host'],
        profile = connectee
    )
    if not connection:
        return 'No connection found', 404
    if connection.status == connection_status.CONNECTED:
        return 'Already connected', 200
    now = datetime.now().astimezone(tz.UTC)
    connection.display_name = request_payload['ack_display_name']
    connection.public_key = request_payload['ack_public_key']
    connection.status =connection_status.CONNECTED
    connection.updated = now
    connection.save()
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
    messages = current_app.datamodels.Message.list(profile=connectee)
    # probably could be pretty significantly optimized in some way

    commentors = defaultdict(set)
    all_commentors = []
    messages_response = {}
    for message in messages:
        for comment_reference in current_app.datamodels.CommentReference.list(
            message_id=message.id
        ):
           commentors[comment_reference.connection.id].add(message.id)
           all_commentors.append(comment_reference.connection)
        if message.files:
            message.files = current_app.url_signer(message.files)
        messages_response[message.id] = message.as_json()
        messages_response[message.id]['comments'] = []

    async def get_comments(connection, message_ids):
        request_payload = {
          'host': request.host,
          'handle': connectee.handle,
          'message_ids': message_ids,
        }
        # enc_and_sign_payload(profile, connection. request_payload)
        # profile is connectee and connection is requestor
        enc_payload, enc_key, signature, nonce, tag = enc_and_sign_payload(
            connectee, requestor, request_payload
        )
        protocol = 'https'
        if connection.host == 'localhost:8080':
            protocol = 'http'
        request_url = f'{protocol}://{connection.host}{url_for("external_comms.retrieve_comments")}'
        payload = {
            'enc_payload': enc_payload,
            'enc_key': enc_key,
            'signature': signature,
            'nonce': nonce,
            'tag': tag,
            'handle': connection.handle,
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
                messages_response[comment['message_id']]['comments'].append(comment)
        else:
            print(f'Unable to retrieve comments {response.status_code}')
            print(response.headers)
            print(response.content)

    async def collect_comments():
        gather = asyncio.gather()
        for commentor in all_commentors:
            asyncio.gather(get_comments(commentor, list(commentors[commentor.id])))
        await gather

    asyncio.run(collect_comments())

    def sorted_list_encoder(o):
        if isinstance(o, SortedList):
            return list(o)
        else:
            return JSONEncoder.default(None, o)

    enc_payload, enc_key, signature, nonce, tag = enc_and_sign_payload(
        connectee, requestor, [m for m in messages_response.values()], json_default=sorted_list_encoder
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
    message_reference = current_app.datamodels.MessageReference(
        connection=requestor,
        message_id=request_payload['message_id'],
    )
    message_reference.save()
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
    # verify message exists
    message = current_app.datamodels.Message.get(id=request_payload['message_id'])
    if not message:
        return f'No message found for id {request_payload["message_id"]}', 404
    comment_reference = current_app.datamodels.CommentReference(
        connection=requestor,
        message_id=request_payload['message_id'],
    )
    comment_reference.save()
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
        comments = current_app.datamodels.Comment.list(message_id=msg_id)
        for comment in comments:
            comment.files = current_app.url_signer(comment.files)
        all_comments.extend([c.as_json() for c in comments])
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
