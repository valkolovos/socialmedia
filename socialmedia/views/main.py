from collections import defaultdict
from Crypto.PublicKey import RSA
from datetime import datetime
from dateutil import tz
from flask import (
    current_app,
    Blueprint,
    jsonify,
    make_response,
    render_template,
    request,
    session,
    url_for,
)
from flask.json import dumps
from flask_login import current_user, logout_user
from google.cloud import datastore, storage

import asyncio
import json
import os
import requests
import uuid
from werkzeug import formparser
from werkzeug.utils import secure_filename

from socialmedia import connection_status
from socialmedia.dataclient import datastore_client
from socialmedia.gcs_object_stream_upload import GCSObjectStreamUpload
from socialmedia.utils import generate_signed_url, TaskManager
from socialmedia.views.utils import (
    enc_and_sign_payload,
    decrypt_payload
)
from socialmedia.views.auth_decorators import verify_user, login_required


storage_client = storage.Client()
task_manager = TaskManager(
    datastore_client.project, 'us-west2',
    os.environ.get('ASYNC_TASKS', 'true').lower() == 'true'
)

blueprint = Blueprint('main', __name__)

def get_user_key():
    _current_user = session['user']
    user_key = datastore_client.key('Profile', _current_user['id'])
    # get full user from datastore
    _current_user = datastore_client.get(user_key)
    crypto_key = RSA.importKey(_current_user['private_key'])
    return crypto_key

@blueprint.route('/')
@login_required
def home():
    context = {"user": session['user']}
    return render_template('index.html', context=context)

@blueprint.route('/validate-session')
@verify_user
def validate_session(user_id):
    return 'valid', 200

@blueprint.route('/sign-out')
def sign_out():
    session.clear()
    if hasattr(current_app, 'login_manager'):
        logout_user()
    return 'signed out', 200

@blueprint.route('/get-messages')
@verify_user
def get_messages(user_id):
    current_user = session['user']
    user_key = datastore_client.key('Profile', current_user['id'])
    query = datastore_client.query(kind='Message')
    query.ancestor = user_key
    query.order = ['-created']
    messages = list(query.fetch())
    # probably could be pretty significantly optimized in some way
    for message in messages:
        if message.get('files'):
            message['files'] = [
                generate_signed_url(
                    '{}.appspot.com'.format(storage_client.project),
                    f,
                ) for f in message['files']
            ]
    response = make_response(jsonify(messages), 200)
    response.headers['Content-Type'] = 'application/json; charset=utf-8'
    return response

@blueprint.route('/get-connection-messages/<connection_id>')
@verify_user
def get_connection_messages(user_id, connection_id):
    current_user = session['user']
    user_key = datastore_client.key('Profile', current_user['id'])
    user = datastore_client.get(user_key)
    connection_key = datastore_client.key(
        'Connection', int(connection_id), parent=user_key
    )
    connection = datastore_client.get(connection_key)
    if not connection:
        return 'No connection found', 404
    request_payload = {
        'host': request.host,
        'handle': user['handle'],
    }
    enc_payload, enc_key, signature, nonce, tag = enc_and_sign_payload(
        user, connection, request_payload
    )
    protocol = 'https'
    if connection['host'] == 'localhost:8080':
        protocol = 'http'
    request_url = f'{protocol}://{connection["host"]}{url_for("external_comms.retrieve_messages")}'
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
        try:
            response_data = json.loads(response.content)
            response_payload = decrypt_payload(
                user,
                response_data['enc_key'],
                response_data['enc_payload'],
                response_data['nonce'],
                response_data['tag'],
            )

            return jsonify(response_payload)
        except Exception as e:
            return f'Failed to decode response {e.message}', 500
    else:
        print(response.content)
        return 'Failed to retrieve connection messages', response.status_code

def custom_stream_factory(
    total_content_length, filename, content_type, content_length=None
):
    filename = secure_filename(filename)
    upload_stream = GCSObjectStreamUpload(
        client=storage_client,
        bucket_name='{}.appspot.com'.format(storage_client.project),
        blob_name=filename,
        content_type=content_type,
    )
    #print("start receiving file ... filename {} => google storage".format(filename))
    upload_stream.start()
    return upload_stream

@blueprint.route('/create-message', methods=['POST'])
@verify_user
def create_message(user_id):
    stream,form,files = formparser.parse_form_data(request.environ, stream_factory=custom_stream_factory)
    current_user = session['user']
    user_key = datastore_client.key('Profile', current_user['id'])
    key = datastore_client.key('Message', parent=user_key)
    message = datastore.Entity(key=key)
    message.update({
        'id': uuid.uuid4().hex,
        'text': form['message'],
        'created': datetime.now().astimezone(tz.UTC),
        'files': [f.stream.saved_filename for f in files.values()]
    })
    datastore_client.put(message)
    payload = {
        'message_id': message['id'],
    }
    task_manager.queue_task(payload, 'message-created', url_for('queue_workers.message_created'))
    file_list = [
        generate_signed_url(
            '{}.appspot.com'.format(storage_client.project),
            f.stream.saved_filename,
        ) for f in files.values()
    ]
    message['files'] = file_list
    return jsonify(message)

@blueprint.route('/manage-connection', methods=['POST'])
@verify_user
def manage_connection(user_id):
    '''
    Accepts or deletes a connection
    If a connection is accepted, the datastore is updated and a
    message is dropped on the connection queue to inform the requestor
    that the the connection has been accepted.
    '''
    current_user = session['user']
    crypto_key = get_user_key()
    try:
        connection_id = int(request.form['connection_id'])
    except:
        return 'Invalid connection_id', 400
    user_key = datastore_client.key('Profile', current_user['id'])
    connection_key = datastore_client.key(
        'Profile', current_user['id'], 'Connection', connection_id
    )
    connection = datastore_client.get(connection_key)
    if not connection:
        return 'No connection found for connectionId {}'.format(connectionId), 404
    if request.form['action'] == 'connect':
        # send acknowledgement - put message on ack-connection queue
        payload = {
            'user_host': request.host,
            'user_key': session['user']['id'],
            'connection_id': connection_id,
        }
        task_manager.queue_task(payload, 'ack-connection', url_for('queue_workers.ack_connection'))
    elif request.form['action'] == 'delete':
        datastore_client.delete(connection.key)
    elif request.form['action'] == 'decline':
        connection.update({
            'status': connection_status.DECLINED,
        })
        datastore_client.put(connection)
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
        'user_key': session['user']['id'],
        'host': request.form['host'],
        'handle': request.form['handle']
    }
    task_manager.queue_task(payload, 'request-connection', url_for('queue_workers.request_connection'))
    return 'connection requested', 200

@blueprint.route('/get-connection-info')
@verify_user
def get_connection_info(user_id):
    current_user = session['user']
    user_key = datastore_client.key('Profile', current_user['id'])
    async def get_message_count(connection):
        query = datastore_client.query(kind='Notification', ancestor=connection.key)
        query.add_filter('type', '=', 'message')
        query.add_filter('read', '=', None)
        query.keys_only()
        connection['unread_message_count'] = len(tuple(query.fetch()))
    query = datastore_client.query(kind='Connection', ancestor=user_key)
    connections = []
    async def get_connections(query):
        gather = asyncio.gather()
        for connection in query.fetch():
            if connection['status'] in (
                connection_status.REQUESTED,
                connection_status.DECLINED,
            ):
                continue
            connection['id'] = connection.id
            connections.append(connection)
            if connection['status'] == connection_status.CONNECTED:
                asyncio.gather(get_message_count(connection))
        await gather
    asyncio.run(get_connections(query))
    return make_response(jsonify(connections), 200)

@blueprint.route('/mark-message-read/<message_id>')
@verify_user
def mark_message_read(user_id, message_id):
    current_user = session['user']
    user_key = datastore_client.key('Profile', current_user['id'])
    query = datastore_client.query(kind='Notification')
    query.ancestor = user_key
    query.add_filter('id', '=', message_id)
    message_notifications = list(query.fetch(limit=1))
    if not message_notifications:
        return 'No such message id', 404
    notif = message_notifications[0]
    notif.update({ 'read': True })
    datastore_client.put(notif)
    return 'marked read', 200

@blueprint.route('/add-comment/<message_id>', methods=['POST'])
@verify_user
def add_comment(user_id, message_id):
    stream,form,files = formparser.parse_form_data(request.environ, stream_factory=custom_stream_factory)
    try:
        connection_id = int(form['connectionId'])
    except ValueError as ve:
        return 'Invalid connection id', 400
    current_user = session['user']
    user_key = datastore_client.key('Profile', current_user['id'])
    key = datastore_client.key('Comment', parent=user_key)
    comment = datastore.Entity(key=key)
    comment_id = uuid.uuid4().hex
    comment.update({
        'id': comment_id,
        'message_id': message_id,
        'text': form['comment'],
        'created': datetime.now().astimezone(tz.UTC),
        'files': [f.stream.saved_filename for f in files.values()]
    })
    datastore_client.put(comment)
    payload = {
        'user_key': current_user['id'],
        'user_host': request.host,
        'message_id': message_id,
        'comment_id': comment_id,
        'connection_key': connection_id,
    }
    task_manager.queue_task(payload, 'comment-created', url_for('queue_workers.comment_created'))
    file_list = [
        generate_signed_url(
            '{}.appspot.com'.format(storage_client.project),
            f.stream.saved_filename,
        ) for f in files.values()
    ]
    comment['files'] = file_list
    return jsonify(comment)
