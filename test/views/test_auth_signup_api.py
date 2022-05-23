import pytest

from datetime import datetime, timedelta
from unittest import mock

from flask import session, current_app
from flask_login import AUTH_HEADER_NAME

from socialmedia import connection_status

from test import datamodels
from .utils import client

def test_signup_first_post(client):
    ''' Tests a first signup post which should result in an admin user. '''
    with mock.patch('socialmedia.views.auth.jwt') as jwt:
        with mock.patch('socialmedia.views.auth.datetime') as dt:
            utcnow_val = datetime(1990, 1, 1, 0, 0)
            dt.utcnow.return_value = utcnow_val
            jwt.encode.return_value = 'token response'
            result = client.post('/signup-api', data={
                'email': 'admin@example.com',
                'password': 'reallyStrongPassword',
                'name': 'Admin User',
                'handle': 'admin_user',
            })
            assert result.status_code == 200
            assert len(result.json.keys()) == 2
            assert all(h in result.json.keys() for h in (AUTH_HEADER_NAME, 'expires'))
            assert result.json[AUTH_HEADER_NAME] == 'token response'
            assert result.json['expires'] == (utcnow_val + timedelta(hours=6)).timestamp()
            assert len(datamodels.Profile._data) == 2
            assert session['user'] == datamodels.Profile._data[1].as_json()

def test_signup_new_user(client):
    ''' Tests a signup post which should result in a non-admin user and a pending connection request
    to the admin user. '''
    admin_user = datamodels.User(
        email='admin@example.com',
        id=2,
        admin=True,
    )
    admin_user.set_password('reallyStrongPassword')
    admin_profile = datamodels.Profile(
        display_name='Admin User',
        handle='admin_handle',
        user_id=2,
    )
    datamodels.User.add_data(admin_user)
    datamodels.Profile.add_data(admin_profile)
    result = client.post('/signup-api', data={
        'email': 'newuser@example.com',
        'password': 'reallyStrongPassword',
        'name': 'New User',
        'handle': 'new_user',
    })
    assert result.status_code == 202
    new_profile = datamodels.Profile.get(handle='new_user')
    client.application.task_manager.queue_task.assert_called_once_with(
        {
            'user_host': 'localhost',
            'user_key': new_profile.user_id,
            'host': 'localhost',
            'handle': 'admin_handle'
        },
        'request-connection',
        '/worker/request-connection'
    )
    # no auth token
    assert result.json is None
    # User and Profile for Admin + User and Profile for new user
    assert len(datamodels.Profile._data) == 4
    assert 'user' not in session

def test_signup_duplicate_user(client):
    ''' Tests a signup post with a duplicate email address which should result in an
    error being returned. '''
    test_email = 'user_already_exists@example.com'

    original_user = datamodels.User(
        email=test_email,
        id=2,
        admin=True,
    )
    original_user.set_password('reallyStrongPassword')
    datamodels.User.add_data(original_user)
    result = client.post('/signup-api', data={
        'email': test_email,
        'password': 'reallyStrongPassword',
        'name': 'Duplicate User',
        'handle': 'duplicate_user',
    })
    assert result.status_code == 401
    client.application.task_manager.queue_task.assert_not_called()
    assert result.json is None
    # Only original user
    assert len(datamodels.Profile._data) == 1
    assert 'user' not in session
    assert b'Unable to add user' in result.data

def test_signup_duplicate_handle(client):
    ''' Tests a signup post which should result in a non-admin user and a pending connection request
    to the admin user. '''
    test_handle = 'admin_handle'

    admin_user = datamodels.User(
        email='admin@example.com',
        id=2,
        admin=True,
    )
    admin_user.set_password('reallyStrongPassword')
    admin_profile = datamodels.Profile(
        display_name='Admin User',
        handle=test_handle,
        user_id=2,
    )
    datamodels.User.add_data(admin_user)
    datamodels.Profile.add_data(admin_profile)
    result = client.post('/signup-api', data={
        'email': 'newuser@example.com',
        'password': 'reallyStrongPassword',
        'name': 'Admin User',
        'handle': test_handle,
    })
    assert result.status_code == 401
    assert result.json is None
    client.application.task_manager.queue_task.assert_not_called()
    # Only admin user and profile
    assert len(datamodels.Profile._data) == 2
    assert 'user' not in session
    assert b'Unable to add user' in result.data

def test_signup_post_missing_form_values(client):
    ''' Tests login without required form values fails and returns appropriate messaging. '''
    result = client.post('/signup-api')
    assert result.json is None
    assert result.status_code == 400
    assert result.data == b'Missing required values email, password, name, handle'
    assert session.get('user') is None
