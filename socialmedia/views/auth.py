import os
import traceback

from datetime import datetime, timedelta

import jwt
from jwt import PyJWTError

from flask import (
    Blueprint,
    current_app,
    request,
    redirect,
    session,
    url_for,
)
from flask_login import AnonymousUserMixin, AUTH_HEADER_NAME, login_user, logout_user, UserMixin

from socialmedia import connection_status
from socialmedia.views.utils import create_profile

auth = Blueprint('auth', __name__)

@auth.route('/login-api', methods=['POST'])
def login_api():
    form_errors = []
    for required_key in ('email', 'password'):
        if not request.form.get(required_key):
            form_errors.append(f'{required_key} required')
    if form_errors:
        return f'Missing required values {", ".join(form_errors)}', 400
    user = _get_user(request.form['email'], request.form['password'])
    if not user:
        return f'User {request.form["email"]} not found or invalid password', 401
    profile = _get_profile(user.id)
    if not user.admin:
        if not _check_admin_connection(profile):
            return 'Request to join still pending', 401
    profile_json = profile.as_json()
    if profile.image:
        profile_json['image'] = current_app.url_signer([profile.image], 7200)[0]
    if profile.cover_image:
        profile_json['cover_image'] = current_app.url_signer([profile.cover_image], 7200)[0]
    session['user'] = profile_json
    login_user(FlaskUser(user.id))
    now = datetime.utcnow()
    expires = now + timedelta(hours=6)
    token = jwt.encode(
        {
            'exp': datetime.utcnow() + timedelta(hours=6),
            'iat': datetime.utcnow(),
            'sub': user.id,
        },
        current_app.config.get('SECRET_KEY'),
        algorithm="HS256"
    )
    return {
        AUTH_HEADER_NAME: token,
        'expires': expires.timestamp()
    }, 200

@auth.route('/signup-api', methods=['POST'])
def signup_api():
    form_errors = {}
    for required_key in ('email', 'password', 'name', 'handle'):
        if not request.form.get(required_key):
            form_errors[required_key] = f'{required_key} required'
    if form_errors:
        return f'Missing required values {", ".join(form_errors)}', 400
    email = request.form['email']
    password = request.form['password']

    # check to see if user already exists
    existing_user = current_app.datamodels.User.get(email=email)
    if existing_user:
        return 'Unable to add user', 401

    # check to see if profile with handle already exists
    existing_profile = current_app.datamodels.Profile.get(handle=request.form['handle'])
    if existing_profile:
        return 'Unable to add user', 401

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
        return 'Request to join pending', 202

    session['user'] = profile.as_json()
    login_user(FlaskUser(user.id), remember=True)
    now = datetime.utcnow()
    expires = now + timedelta(hours=6)
    token = jwt.encode(
        {
            'exp': datetime.utcnow() + timedelta(hours=6),
            'iat': datetime.utcnow(),
            'sub': user.id,
        },
        current_app.config.get('SECRET_KEY'),
        algorithm="HS256"
    )
    return {
        AUTH_HEADER_NAME: token,
        'expires': expires.timestamp()
    }, 200

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
    return user_profile

def load_user(user_id):
    user = session.get('authenticated_user')
    if not user:
        user = current_app.datamodels.User.get(id=user_id)
        if user:
            session['authenticated_user'] = user.as_json()
            profile = _get_profile(user.id)
            profile_json = profile.as_json()
            if profile.image:
                profile_json['image'] = current_app.url_signer(profile.image, 7200)
            if profile.cover_image:
                profile_json['cover_image'] = current_app.url_signer(profile.cover_image, 7200)
            session['user'] = profile_json
        else:
            return None
    return FlaskUser(user_id)

def request_loader(request):
    token = request.headers.get(AUTH_HEADER_NAME)
    user = None
    if token:
        try:
            payload = jwt.decode(token, current_app.config.get('SECRET_KEY'), algorithms=["HS256"])
        except PyJWTError:
            print(traceback.format_exc())
            return None
        user_id = payload.get('sub')
        user = current_app.datamodels.User.get(id=user_id)
        if user:
            session['authenticated_user'] = user.as_json()
            profile = _get_profile(user.id)
            profile_json = profile.as_json()
            if profile.image:
                profile_json['image'] = current_app.url_signer([profile.image], 7200)[0]
            if profile.cover_image:
                profile_json['cover_image'] = current_app.url_signer([profile.cover_image], 7200)[0]
            session['user'] = profile_json
            setattr(request, 'current_profile', profile)
    if user:
        return FlaskUser(user.id)
    return None

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

