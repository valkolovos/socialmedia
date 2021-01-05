import functools

from flask import request, session, current_app
from flask_login import current_user
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token


class UnauthorizedException(Exception):
    pass

def verify_firebase():
    if not request.headers.get('Authorization'):
        raise UnauthorizedException()
    if not session.get('auth_user_id'):
        token = request.headers['Authorization'].split(' ').pop()
        google_request = google_requests.Request()
        id_info = id_token.verify_firebase_token(token, google_request)
        if not id_info:
            raise UnauthorizedException()
        auth_user_id = id_info['sub']
        session['auth_user_id'] = auth_user_id
    else:
        auth_user_id = session.get('auth_user_id')
    return auth_user_id

def verify_flask():
    if not current_user.is_authenticated:
        raise UnauthorizedException()
    return current_user.id

def verify_user(func):
    @functools.wraps(func)
    def verify_wrapper(*args, **kwargs):
        if hasattr(current_app, 'login_manager'):
            auth_func = verify_flask
        else:
            auth_func = verify_firebase
        try:
            auth_user_id = auth_func()
        except UnauthorizedException:
            return 'Unauthorized', 401
        kwargs['user_id'] = auth_user_id
        return func(*args, **kwargs)
    return verify_wrapper

def login_required(func):
    @functools.wraps(func)
    def login_required_wrapper(*args, **kwargs):
        if hasattr(current_app, 'login_manager') and not current_user.is_authenticated:
            return current_app.login_manager.unauthorized()
        return func(*args, **kwargs)
    return login_required_wrapper

