import os

from uuid import uuid4
from Crypto.Hash import SHA256
from flask import Blueprint, render_template, request, redirect, session, url_for
from flask_login import login_user, logout_user, UserMixin
from google.cloud import datastore

from socialmedia import connection_status
from socialmedia.views.utils import create_profile
from socialmedia.dataclient import datastore_client
from socialmedia.utils import TaskManager

auth = Blueprint('auth', __name__)
task_manager = TaskManager(
    datastore_client.project, 'us-west2',
    os.environ.get('ASYNC_TASKS', 'true').lower() == 'true'
)

@auth.route('/login', methods=['GET'])
def login():
    return render_template('login.html', form_errors={})

@auth.route('/login-api', methods=['POST'])
def login_api():
    form_errors = []
    for required_key in ('email', 'password'):
        if not request.form.get(required_key):
            form_errors.append(f'{required_key} required')
    if form_errors:
        return 'Missing required values {}'.format(', '.join(form_errors)), 400
    user = _get_user(request.form['email'], request.form['password'])
    if not user:
        return f'User {request.form["email"]} not found or invalid password', 401
    profile = _get_profile(user['id'])
    session['user'] = profile
    login_user(User(user['id']))
    return 'User logged in', 200

@auth.route('/login', methods=['POST'])
def login_post():
    form_errors = {}
    for required_key in ('email', 'password'):
        if not request.form.get(required_key):
            form_errors[required_key] = f'{required_key} required'
    if form_errors:
        return render_template(
            'login.html',
            form_errors=form_errors,
            **request.form
        )
    user = _get_user(request.form['email'], request.form['password'])
    if not user:
        return render_template(
            'login.html',
            form_errors={},
            error='Error logging in',
            **request.form
        )
    profile = _get_profile(user['id'])
    if not user['admin']:
        # check for active admin user connection
        query = datastore_client.query(kind='User')
        query.add_filter('admin', '=', True)
        admin_users = list(query.fetch(limit=1))
        admin_profile = _get_profile(admin_users[0]['id'])
        # checking for connection FROM admin TO user
        # the other way around might not correctly be in sync
        query = datastore_client.query(kind='Connection')
        query.ancestor=admin_profile.key
        query.add_filter('host', '=', request.host)
        query.add_filter('handle', '=', profile['handle'])
        connections = list(query.fetch(limit=1))
        if not connections or connections[0]['status'] != connection_status.CONNECTED:
            return 'Request to join still pending', 401

    session['user'] = profile
    login_user(User(user['id']), remember=True)
    return redirect(url_for('main.home'))

@auth.route('/signup', methods=['GET'])
def signup():
    return render_template('sign_up.html', form_errors={})

@auth.route('/signup', methods=['POST'])
def signup_post():
    form_errors = {}
    for required_key in ('email', 'password', 'name', 'handle'):
        if not request.form.get(required_key):
            form_errors[required_key] = f'{required_key} required'
    if form_errors:
        return render_template(
            'sign_up.html',
            form_errors=form_errors,
            **request.form
        )
    email = request.form['email']
    password = request.form['password']

    # check to see if user already exists
    query = datastore_client.query(kind='User')
    query.add_filter('email', '=', email)
    users = list(query.fetch(limit=1))
    if users:
        # intentionally returning vague message
        # to avoid email validation
        return render_template(
            'sign_up.html',
            error='Unable to add user',
            form_errors={},
            **request.form
        )
    h = SHA256.new()
    h.update(bytes(password, 'utf-8'))
    enc_passwd = h.hexdigest()
    key = datastore_client.key('User')
    user = datastore.Entity(key=key)
    user_id = str(uuid4())

    user_data = {
        'id': user_id,
        'email': request.form['email'],
        'password': enc_passwd,
        'admin': False,
    }

    # check to see if there is an admin user
    query = datastore_client.query(kind='User')
    query.add_filter('admin', '=', True)
    admin_users = list(query.fetch(limit=1))
    if not admin_users:
        # first user added is going to be admin
        user_data['admin'] = True

    user.update(user_data)
    datastore_client.put(user)
    profile = create_profile(user_id, request.form['name'], request.form['handle'])

    # if this is not an admin user, request a connection to the admin user
    # an established connection with the admin user allows the new user access
    if admin_users:
        # get admin user profile
        query = datastore_client.query(kind='Profile')
        query.add_filter('user_id', '=', admin_users[0]['id'])
        admin_profiles = list(query.fetch(limit=1))
        payload = {
            'user_host': request.host,
            'user_key': profile.id,
            'host': request.host,
            'handle': admin_profiles[0]['handle']
        }
        task_manager.queue_task(
            payload, 'request-connection', url_for('queue_workers.request_connection')
        )
        return 'Request to join pending', 401

    login_user(User(user_id), remember=True)
    profile['id'] = profile.id
    session['user'] = profile
    return redirect(url_for('main.home'))

@auth.route('/logout')
def logout():
    session.pop('authenticated_user')
    logout_user()
    return 'Logout'

def _get_user(email, password):
    h = SHA256.new()
    h.update(bytes(password, 'utf-8'))
    enc_passwd = h.hexdigest()
    query = datastore_client.query(kind='User')
    query.add_filter('email', '=', email)
    query.add_filter('password', '=', enc_passwd)
    users = list(query.fetch(limit=1))
    if users:
        return users[0]
    return None

def _get_profile(user_id):
    query = datastore_client.query(kind='Profile')
    query.add_filter('user_id', '=', user_id)
    profiles = list(query.fetch(limit=1))
    if not profiles:
        raise Exception('User without profile found')
    # removing private_key from user object in session
    profiles[0]['private_key'] = None
    # adding id to use for key creation later
    profiles[0]['id'] = profiles[0].id
    return profiles[0]


def load_user(user_id):
    user = session.get('authenticated_user')
    if not user:
        query = datastore_client.query(kind='User')
        query.add_filter('id', '=', user_id)
        users = list(query.fetch(limit=1))
        if users:
            user = users[0]
            session['authenticated_user'] = user
    return User(user['id'])

class User(UserMixin):
    def __init__(self, id):
        self.id = id
