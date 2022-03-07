import os

from uuid import uuid4
from Crypto.Hash import SHA256
from flask import current_app, Blueprint, render_template, request, redirect, session, url_for
from flask_login import login_user, logout_user, UserMixin

from socialmedia import connection_status
from socialmedia.views.utils import create_profile

auth = Blueprint('auth', __name__)

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
    profile = _get_profile(user.id)
    if not user.admin:
        if not _check_admin_connection(profile):
            return 'Request to join still pending', 401
    session['user'] = profile.as_json()
    login_user(FlaskUser(user.id))
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
    profile = _get_profile(user.id)
    if not user.admin:
        if not _check_admin_connection(profile):
            return 'Request to join still pending', 401

    session['user'] = profile.as_json()
    login_user(FlaskUser(user.id), remember=True)
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
    existing_user = current_app.datamodels.User.get(email=email)
    if existing_user:
        # intentionally returning vague message
        # to avoid email validation
        return render_template(
            'sign_up.html',
            error='Unable to add user',
            form_errors={},
            **request.form
        )

    # check to see if profile with handle already exists
    existing_profile = current_app.datamodels.Profile.get(handle=request.form['handle'])
    if existing_profile:
        # intentionally returning vague message
        # to avoid email validation
        return render_template(
            'sign_up.html',
            error='Unable to add user',
            form_errors={},
            **request.form
        )

    user = current_app.datamodels.User(
        id=current_app.datamodels.User.generate_uuid(),
        email=request.form['email'],
        admin=False
    )
    user.set_password(password)

    # check to see if there is an admin user
    admin_user = current_app.datamodels.User.get(
        admin=True
    )
    if not admin_user:
        # first user added is going to be admin
        user.admin = True

    user.save()
    profile = create_profile(user.id, request.form['name'], request.form['handle'])

    # if this is not an admin user, request a connection to the admin user
    # an established connection with the admin user allows the new user access
    if not user.admin:
        # get admin user profile
        admin_profile = current_app.datamodels.Profile.get(
            user_id=admin_user.id
        )
        payload = {
            'user_host': request.host,
            'user_key': profile.user_id,
            'host': request.host,
            'handle': admin_profile.handle
        }
        current_app.task_manager.queue_task(
            payload, 'request-connection', url_for('queue_workers.request_connection')
        )
        return 'Request to join pending', 401

    login_user(FlaskUser(user.id), remember=True)
    session['user'] = profile.as_json()
    return redirect(url_for('main.home'))

@auth.route('/logout')
def logout():
    session.pop('authenticated_user')
    logout_user()
    return 'Logout'

def _get_user(email, password):
    enc_passwd = current_app.datamodels.User.enc_password(password)
    return current_app.datamodels.User.get(
        email=email,
        password=enc_passwd
    )

def _get_profile(user_id):
    user_profile = current_app.datamodels.Profile.get(
        user_id=user_id
    )
    if not user_profile:
        raise Exception('User without profile found')
    user_profile.private_key = None
    return user_profile

def load_user(user_id):
    user = session.get('authenticated_user')
    if not user:
        user = current_app.datamodels.User.get(id=user_id)
        if user:
            session['authenticated_user'] = user.as_json()
        else:
            return None
    return FlaskUser(user_id)

def _check_admin_connection(profile):
    # check for active admin user connection
    admin_user = current_app.datamodels.User.get(
        admin=True
    )
    if not admin_user:
        print('no admin user exists')
        return False
    admin_profile = _get_profile(admin_user.id)
    # checking for connection FROM admin TO user
    # the other way around might not correctly be in sync
    connection = current_app.datamodels.Connection.get(
        profile=admin_profile,
        host=request.host,
        handle=profile.handle
    )
    if not connection or connection.status != connection_status.CONNECTED:
        return False
    return True

class FlaskUser(UserMixin):
    def __init__(self, id):
        self.id = id
