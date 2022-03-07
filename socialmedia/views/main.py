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

import asyncio
import json
import os
import requests
from werkzeug import formparser
from werkzeug.utils import secure_filename

from socialmedia import connection_status
from socialmedia.views.utils import (
    enc_and_sign_payload,
    decrypt_payload
)
from socialmedia.views.auth_decorators import verify_user, login_required


blueprint = Blueprint('main', __name__)

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
    current_profile = current_app.datamodels.Profile.get(user_id=session['user']['user_id'])
    messages = current_app.datamodels.Message.list(profile=current_profile, order=['-created'])
    # probably could be pretty significantly optimized in some way
    for message in messages:
        message.files = current_app.url_signer(message.files)
    response = jsonify([m.as_json() for m in messages])
    return response

@blueprint.route('/get-connection-messages/<connection_id>')
@verify_user
def get_connection_messages(user_id, connection_id):
    current_profile = current_app.datamodels.Profile.get(user_id=session['user']['user_id'])
    connection = current_app.datamodels.Connection.get(id=connection_id)
    if not connection:
        return f'No connection found ({connection_id})', 404
    request_payload = {
        'host': request.host,
        'handle': current_profile.handle
    }
    enc_payload, enc_key, signature, nonce, tag = enc_and_sign_payload(
        current_profile, connection, request_payload
    )
    protocol = 'https'
    if connection.host == 'localhost:8080':
        protocol = 'http'
    request_url = f'{protocol}://{connection.host}{url_for("external_comms.retrieve_messages")}'
    response = requests.post(
        request_url,
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
        try:
            response_data = json.loads(response.content)
            response_payload = decrypt_payload(
                current_profile,
                response_data['enc_key'],
                response_data['enc_payload'],
                response_data['nonce'],
                response_data['tag'],
            )

            return jsonify(response_payload)
        except Exception as e:
            return f'Failed to decode response: {e}', 500
    else:
        print(response.content)
        return 'Failed to retrieve connection messages', response.status_code

@blueprint.route('/create-message', methods=['POST'])
@verify_user
def create_message(user_id):
    stream,form,files = formparser.parse_form_data(request.environ, stream_factory=current_app.stream_factory)
    current_profile = current_app.datamodels.Profile.get(user_id=session['user']['user_id'])
    # the custom stream factories _should_ be using 'secure_filename' when processing,
    # so need to make sure the message filenames are the same
    #
    # this is kinda gross, and there's probably a better way to do it, but it
    # works for now
    message = current_app.datamodels.Message(
        profile = current_profile,
        text = form['message'],
        files = [secure_filename(f.filename) for f in files.values()]
    )
    message.save()

    # reset filenames to signed urls to return to UI
    file_list = current_app.url_signer([filename for filename in message.files])
    message.files = file_list
    payload = {
        'message_id': message.id,
    }
    current_app.task_manager.queue_task(payload, 'message-created', url_for('queue_workers.message_created'))
    return jsonify(message.as_json())

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
    current_user = current_app.datamodels.Profile.get(user_id=session['user']['user_id'])
    async def get_message_count(connection):
        unread_messages = current_app.datamodels.MessageReference.list(
            connection=connection, read=None,
        )
        setattr(connection, 'unread_message_count', len(unread_messages))
    connections = current_app.datamodels.Connection.list(profile=current_user)
    async def get_connections(connections):
        gather = asyncio.gather()
        for connection in connections:
            if connection.status == connection_status.CONNECTED:
                asyncio.gather(get_message_count(connection))
        await gather
    asyncio.run(get_connections(connections))
    response = []
    for c in connections:
        if c.status in (
            connection_status.REQUESTED,
            connection_status.DECLINED,
        ):
            continue
        c_json = c.as_json()
        c_json['unread_message_count'] = getattr(c, 'unread_message_count', 0)
        response.append(c_json)
    return jsonify(response)

@blueprint.route('/mark-message-read/<message_id>')
@verify_user
def mark_message_read(user_id, message_id):
    message_reference = current_app.datamodels.MessageReference.get(message_id=message_id)
    if not message_reference:
        return f'No such message id ({message_id})', 404
    message_reference.read = True
    message_reference.save()
    return f'message id {message_id} marked read', 200

@blueprint.route('/add-comment/<message_id>', methods=['POST'])
@verify_user
def add_comment(user_id, message_id):
    current_profile = current_app.datamodels.Profile.get(user_id=session['user']['user_id'])
    stream,form,files = formparser.parse_form_data(request.environ, stream_factory=current_app.stream_factory)
    connection_id = form['connectionId']
    connection = current_app.datamodels.Connection.get(id=connection_id)
    if not connection:
        return f'Connection id ({connection_id}) not found', 404
    comment = current_app.datamodels.Comment(
        profile=current_profile,
        message_id=message_id,
        text=form['comment'],
        created=datetime.now().astimezone(tz.UTC),
        files=[secure_filename(f.filename) for f in files.values()],
    )
    comment.save()
    payload = {
        'user_key': current_profile.user_id,
        'user_host': request.host,
        'message_id': message_id,
        'comment_id': comment.id,
        'connection_key': connection.id,
    }
    current_app.task_manager.queue_task(payload, 'comment-created', url_for('queue_workers.comment_created'))
    comment.files = current_app.url_signer(files)
    return jsonify(comment.as_json())
