import base64
import dateparser
import json
import requests

from collections import defaultdict
from datetime import datetime
from dateutil import tz
from flask import Blueprint, current_app, jsonify, request, url_for

from socialmedia import connection_status, models
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
    get_post_comments,
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
        read=False,
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

@blueprint.route('/get-profile-info', methods=['POST'])
@json_request
@validate_request
@validate_handle
@validate_payload(fields=('host', 'handle'))
@validate_connection
def get_profile_info(request_data, connectee, request_payload, requestor):
    ''' Gets profile info for display on requestor's side
        request should be JSON:
        {
          'host': 'requestor hostname',
          'handle': 'requestor handle',
        }
        returns profile information
    '''
    post_count = current_app.datamodels.Post.count(profile=connectee)

    enc_payload, enc_key, signature, nonce, tag = enc_and_sign_payload(
        connectee, requestor, { 'post_count': post_count }
    )
    return jsonify(
        enc_payload=enc_payload,
        enc_key=enc_key,
        signature=signature,
        nonce=nonce,
        tag=tag
    ), 200

@blueprint.route('/retrieve-posts', methods=['POST'])
@json_request
@validate_request
@validate_handle
@validate_payload(fields=('host', 'handle'))
@validate_connection
def retrieve_posts(request_data, connectee, request_payload, requestor):
    ''' Requests posts for given handle
        request should be JSON:
        {
          'host': 'requestor hostname',
          'handle': 'requestor handle',
        }
        returns posts
    '''
    posts = current_app.datamodels.Post.list(profile=connectee, order=['-created'])
    # probably could be pretty significantly optimized in some way

    comment_references = defaultdict(list)
    for post in posts:
        for comment_reference in current_app.datamodels.CommentReference.list(
            post_id=post.id
        ):
            comment_references[post.id].append(comment_reference)
        if post.files:
            post.files = current_app.url_signer(post.files)

    get_post_comments(posts, comment_references, request.host)

    enc_payload, enc_key, signature, nonce, tag = enc_and_sign_payload(
        connectee, requestor, [m.as_json() for m in posts]
    )
    return jsonify(
        enc_payload=enc_payload,
        enc_key=enc_key,
        signature=signature,
        nonce=nonce,
        tag=tag
    ), 200


@blueprint.route('/post-notify', methods=['POST'])
@json_request
@validate_request
@validate_handle
@validate_payload(
    fields=(
        'post_host', 'post_handle', 'post_id',
    )
)
@validate_connection(host_key='post_host', handle_key='post_handle')
def post_notify(request_data, connectee, request_payload, requestor):
    ''' Notification endpoint for notification of posts from other connections
        enc_payload should be JSON:
        {
          'post_host': 'hostname',
          'post_handle': 'requestor handle',
          'post_id': 'id of new post',
        }
    '''
    post_reference = current_app.datamodels.PostReference(
        connection=requestor,
        post_id=request_payload['post_id'],
        reference_read=False,
        read=False
    )
    post_reference.save()
    return '', 200

@blueprint.route('/comment-created', methods=['POST'])
@json_request
@validate_request
@validate_handle
@validate_payload(
    fields=(
        'comment_host', 'comment_handle', 'post_id', 'comment_id',
    )
)
@validate_connection(host_key='comment_host', handle_key='comment_handle')
def comment_created(request_data, connectee, request_payload, requestor):
    ''' Notification endpoint for notification of new comment on a post
        enc_payload should be JSON:
        {
          'comment_host': 'commenter hostname',
          'comment_handle': 'commenter handle',
          'post_id': 'id of post commented on',
          'comment_id': 'id of comment'
        }
    '''
    # verify post exists
    post = current_app.datamodels.Post.get(id=request_payload['post_id'])
    if not post:
        return f'No post found for id {request_payload["post_id"]}', 404
    comment_reference = current_app.datamodels.CommentReference(
        connection=requestor,
        post_id=request_payload['post_id'],
    )
    comment_reference.save()
    return '', 200

@blueprint.route('/retrieve-comments', methods=['POST'])
@json_request
@validate_request
@validate_handle
@validate_payload(
    fields=(
        'host', 'handle', 'post_ids',
    )
)
@validate_connection()
def retrieve_comments(request_data, connectee, request_payload, requestor):
    ''' Requests comments for a list of posts
        enc_payload should be JSON:
        {
          'host': 'requestor host',
          'handle': 'requestor handle',
          'post_ids': ['array of post ids'],
        }
    '''
    all_comments = []
    for msg_id in request_payload['post_ids']:
        comments = current_app.datamodels.Comment.list(post_id=msg_id)
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
