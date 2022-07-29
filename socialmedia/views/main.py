from collections import defaultdict
from dateparser import parse
from datetime import datetime
from dateutil import tz
from flask import (
    current_app,
    Blueprint,
    jsonify,
    request,
    session,
    url_for,
)
from flask_login import logout_user

import asyncio
import base64
import json
import re
import requests
from werkzeug import formparser
from werkzeug.utils import secure_filename

from socialmedia import connection_status
from socialmedia.views.utils import (
    enc_and_sign_payload,
    decrypt_payload,
    get_post_comments,
)
from socialmedia.views.auth_decorators import verify_user


blueprint = Blueprint('main', __name__)

@blueprint.route('/validate-session', methods=['OPTIONS'])
def handle_validate_options():
    return '', 200

@blueprint.route('/validate-session')
@verify_user
def validate_session(user_id):
    return session['user'], 200

@blueprint.route('/sign-out')
def sign_out():
    if hasattr(current_app, 'login_manager'):
        logout_user()
    session.clear()
    return 'signed out', 200

@blueprint.route('/get-posts')
@verify_user
def get_posts(user_id):
    current_profile = request.current_profile
    comment_references = defaultdict(list)
    posts = current_app.datamodels.Post.list(profile=current_profile, order=['-created'])
    for post in posts:
        post.files = current_app.url_signer(post.files)
        for comment_reference in current_app.datamodels.CommentReference.list(
            post_id=post.id
        ):
            comment_references[post.id].append(comment_reference)
    get_post_comments(posts, comment_references, request.host)
    response = jsonify([m.as_json() for m in posts])
    return response

@blueprint.route('/get-connection-posts/<connection_id>')
@verify_user
def get_connection_posts(user_id, connection_id):
    current_profile = request.current_profile
    connection = current_app.datamodels.Connection.get(id=connection_id)
    if not connection:
        return f'No connection found ({connection_id})', 404

    request_payload = {
        'host': request.host,
        'handle': current_profile.handle
    }
    request_url = f'{connection.host}{url_for("external_comms.retrieve_posts")}'
    try:
        posts = _perform_secure_request(request_url, current_profile, request_payload, connection)
        post_reference_map = {
            pr.post_id: pr
            for pr in current_app.datamodels.PostReference.list(
                connection=connection,
                read=False
            )
        }
        for post in posts:
            post_reference = post_reference_map.get(post['id'])
            if post_reference:
                post['read'] = post_reference.read
        return jsonify(posts)
    except SecureRequestException as sre:
        print(sre.response.content)
        return 'Failed to retrieve connection posts', sre.response.status_code
    except Exception as e:
        return f'Failed to decode response: {e}', 500

@blueprint.route('/create-post', methods=['POST'])
@verify_user
def create_post(user_id):
    stream,form,files = formparser.parse_form_data(request.environ, stream_factory=current_app.stream_factory)
    current_profile = request.current_profile
    # the custom stream factories _should_ be using 'secure_filename' when processing,
    # so need to make sure the post filenames are the same
    #
    # this is kinda gross, and there's probably a better way to do it, but it
    # works for now
    post = current_app.datamodels.Post(
        profile = current_profile,
        text = form['post'],
        files = [secure_filename(f.filename) for f in files.values()]
    )
    post.save()

    # reset filenames to signed urls to return to UI
    file_list = current_app.url_signer([filename for filename in post.files])
    post.files = file_list
    payload = {
        'post_id': post.id,
    }
    current_app.task_manager.queue_task(payload, 'post-created', url_for('queue_workers.post_created'))
    return jsonify(post.as_json())

@blueprint.route('/manage-connection', methods=['POST'])
@verify_user
def manage_connection(user_id):
    '''
    Accepts or deletes a connection
    If a connection is accepted, the datastore is updated and a
    message is dropped on the connection queue to inform the requestor
    that the the connection has been accepted.
    '''
    current_user = current_app.datamodels.Profile.get(user_id=user_id)
    try:
        connection_id = request.form['connection_id']
    except:
        return 'Invalid connection_id', 400
    connection = current_app.datamodels.Connection.get(id=connection_id)
    if not connection:
        return f'No connection found for connectionId {connection_id}', 404
    if request.form['action'] == 'connect':
        # send acknowledgement - put message on ack-connection queue
        payload = {
            'user_host': request.host,
            'user_key': user_id,
            'connection_id': connection_id,
        }
        current_app.task_manager.queue_task(payload, 'ack-connection', url_for('queue_workers.ack_connection'))
        connection.status = connection_status.CONNECTED
        connection.read = True
        connection.save()
    elif request.form['action'] == 'delete':
        connection.delete()
    elif request.form['action'] == 'decline':
        connection.status = connection_status.DECLINED
        connection.save()
    else:
        return f'Invalid action requested - {request.form["action"]}', 400
    return '{} completed'.format(request.form['action']), 200

@blueprint.route('/request-connection', methods=['POST'])
@verify_user
def request_connection(user_id):
    '''
    Drops a request on the queue that will call out to other user's server to
    request access
    '''
    payload = {
        'user_host': request.host,
        'user_key': session['user']['user_id'],
        'host': request.form['host'],
        'handle': request.form['handle']
    }
    current_app.task_manager.queue_task(payload, 'request-connection', url_for('queue_workers.request_connection'))
    return 'connection requested', 200

@blueprint.route('/get-connection-info')
@verify_user
def get_connection_info(user_id):
    current_profile = request.current_profile
    async def get_post_count(connection):
        post_references = current_app.datamodels.PostReference.list(
            connection=connection
        )
        total_post_count = 0
        request_payload = {
            'host': request.host,
            'handle': current_profile.handle
        }
        request_url = f'{connection.host}{url_for("external_comms.get_profile_info")}'
        try:
            response = _perform_secure_request(
                request_url, current_profile, request_payload, connection
            )
            total_post_count = response['post_count']
        except SecureRequestException as sre:
            print(sre)
        setattr(connection, 'post_references', [m.as_json() for m in post_references])
        setattr(connection, 'total_post_count', total_post_count)
    connections = current_app.datamodels.Connection.list(profile=current_profile)
    async def get_connections(connections):
        gather = asyncio.gather()
        for connection in connections:
            if connection.status == connection_status.CONNECTED:
                asyncio.gather(get_post_count(connection))
        await gather
    asyncio.run(get_connections(connections))
    response = {
        'connections': [],
        'post_references': []
    }
    for c in connections:
        if c.status in (
            connection_status.REQUESTED,
            connection_status.DECLINED,
        ):
            continue
        c_json = c.as_json()
        c_json['total_post_count'] = getattr(c, 'total_post_count', 0)
        c_json['post_references'] = getattr(c, 'post_references', [])
        response['connections'].append(c_json)
        response['post_references'].extend(getattr(c, 'post_references', []))
    def created_key(post_reference_json):
        return parse(post_reference_json['created'])
    response['post_references'].sort(key=created_key, reverse=True)
    return jsonify(response)

@blueprint.route('/mark-post-read/<post_id>')
@verify_user
def mark_post_read(user_id, post_id):
    current_profile = request.current_profile
    post_reference = current_app.datamodels.PostReference.get(
        post_id=post_id, profile=current_profile
    )
    if not post_reference:
        return f'No such post id ({post_id})', 404
    post_reference.read = True
    post_reference.reference_read = True
    post_reference.save()
    return f'post id {post_id} marked read', 200

@blueprint.route('/mark-connection-read/<connection_id>')
@verify_user
def mark_connection_read(user_id, connection_id):
    connection = current_app.datamodels.Connection.get(id=connection_id)
    if not connection:
        return f'No such connection ({connection_id})', 404
    connection.read = True
    connection.save()
    return f'connection id {connection_id} marked read', 200

@blueprint.route('/mark-post-reference-read/<post_id>')
@verify_user
def mark_post_reference_read(user_id, post_id):
    current_profile = request.current_profile
    post_reference = current_app.datamodels.PostReference.get(
        post_id=post_id, profile=current_profile
    )
    if not post_reference:
        return f'No such post_reference ({user_id}:{post_id})', 404
    post_reference.reference_read = True
    post_reference.save()
    return f'post_reference {user_id}:{post_id} marked read', 200

@blueprint.route('/add-comment/<post_id>', methods=['POST'])
@verify_user
def add_comment(user_id, post_id):
    current_profile = request.current_profile
    stream,form,files = formparser.parse_form_data(request.environ, stream_factory=current_app.stream_factory)
    connection = None
    if not current_app.datamodels.Post.get(id=post_id, profile=current_profile):
        connection_id = form['connectionId']
        connection = current_app.datamodels.Connection.get(id=connection_id)
        if not connection:
            return f'Connection id ({connection_id}) not found', 404
    comment = current_app.datamodels.Comment(
        profile=current_profile,
        post_id=post_id,
        text=form['comment'],
        created=datetime.now().astimezone(tz.UTC),
        files=[secure_filename(f.filename) for f in files.values()],
    )
    comment.save()
    if connection:
        payload = {
            'user_key': current_profile.user_id,
            'user_host': request.host,
            'post_id': post_id,
            'comment_id': comment.id,
            'connection_key': connection.id,
        }
        current_app.task_manager.queue_task(payload, 'comment-created', url_for('queue_workers.comment_created'))
    comment.files = current_app.url_signer(files)
    return jsonify(comment.as_json())


@blueprint.route('/update-profile-images', methods=['OPTIONS'])
def update_profile_images_options():
    return '', 200

@blueprint.route('/update-profile-images', methods=['POST'])
@verify_user
def update_profile_images(user_id):
    current_profile = request.current_profile
    profile_json = current_profile.as_json()
    if request.form.get('profileImage'):
        filename = _upload(request.form['profileImage'], 'profile', current_profile)
        current_profile.image = filename
        profile_json['image'] = current_app.url_signer([current_profile.image], 7200)[0]
    if request.form.get('coverImage'):
        filename = _upload(request.form['coverImage'], 'cover', current_profile)
        current_profile.cover_image = filename
        profile_json['cover_image'] = current_app.url_signer([current_profile.cover_image], 7200)[0]
    current_profile.save()
    return profile_json, 200

class SecureRequestException(Exception):
    def __init__(self, response):
        self.response = response
        super().__init__(response.content)

def _perform_secure_request(url, current_profile, payload, connection):
    _timer = datetime.now()
    enc_payload, enc_key, signature, nonce, tag = enc_and_sign_payload(
        current_profile, connection, payload
    )
    protocol = 'https'
    if connection.host == 'localhost:8080': # pragma: no cover
        protocol = 'http'
    response = requests.post(
        f'{protocol}://{url}',
        json={
            'enc_payload': enc_payload,
            'enc_key': enc_key,
            'signature': signature,
            'nonce': nonce,
            'tag': tag,
            'handle': connection.handle,
        }
    )
    if response.status_code == 200:
        response_data = json.loads(response.content)
        response_payload = decrypt_payload(
            current_profile,
            response_data['enc_key'],
            response_data['enc_payload'],
            response_data['nonce'],
            response_data['tag'],
        )
        print(f'_perform_secure_request({url}): {(datetime.now() - _timer).total_seconds()}')
        return response_payload
    else:
        raise SecureRequestException(response)

def _upload(image_data, image_type, current_profile):
    # data is in format "data:[content_type];[encoding],[base64 data]"
    m = re.search(r'data:([^;]*);[^,]*,(.*)', image_data)
    content_type, b64_data = m.groups()
    img_binary_data = base64.b64decode(b64_data)
    filename = secure_filename(f'{current_profile.user_id}-{image_type}.{content_type.split("/")[1]}')
    stream = current_app.stream_factory(
        len(img_binary_data), filename, content_type
    )
    stream.write(img_binary_data)
    stream.stop()
    return filename

