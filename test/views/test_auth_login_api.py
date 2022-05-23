from datetime import datetime, timedelta
from unittest import mock

from flask import session
from flask_login import AUTH_HEADER_NAME

from socialmedia import connection_status
from test import datamodels
from .utils import client

def test_login_api(client):
    ''' Tests a standard login. User must have valid connection with admin user. '''
    testUser = datamodels.User(
        email='gooduser@example.com',
        id=1,
    )
    testUser.set_password('reallyStrongPassword')
    testUser.save()
    adminUser = datamodels.User(
        email='admin@example.com',
        id=2,
        admin=True,
    )
    adminUser.set_password('reallyStrongPassword')
    adminUser.save()
    testProfile = datamodels.Profile(
        display_name='Test User',
        handle='test_handle',
        user_id=1,
    )
    testProfile.save()
    adminProfile = datamodels.Profile(
        display_name='Admin User',
        handle='admin_handle',
        user_id=2,
    )
    adminProfile.save()
    adminConnection = datamodels.Connection(
        profile=adminProfile,
        host='localhost',
        handle='test_handle',
        status=connection_status.CONNECTED,
    )
    adminConnection.save()
    with mock.patch('socialmedia.views.auth.jwt') as jwt:
        with mock.patch('socialmedia.views.auth.datetime') as dt:
            utcnow_val = datetime(1990, 1, 1, 0, 0)
            dt.utcnow.return_value = utcnow_val
            jwt.encode.return_value = 'token response'
            result = client.post('/login-api', data={
                'email': 'gooduser@example.com',
                'password': 'reallyStrongPassword',
            })
            assert result.status_code == 200
            assert len(result.json.keys()) == 2
            assert all(h in result.json.keys() for h in (AUTH_HEADER_NAME, 'expires'))
            assert result.json[AUTH_HEADER_NAME] == 'token response'
            assert result.json['expires'] == (utcnow_val + timedelta(hours=6)).timestamp()
            assert session['user'] == testProfile.as_json()

def test_login_api_no_user(client):
    ''' Tests login with non-existent user fails '''
    result = client.post('/login-api', data={
        'email': 'notfounduser@example.com',
        'password': 'reallyStrongPassword',
    })
    assert result.status_code == 401
    assert result.data == b'User notfounduser@example.com not found or invalid password'

def test_login_api_no_profile(client):
    adminUser = datamodels.User(
        email='admin@example.com',
        id=2,
        admin=True,
    )
    adminUser.set_password('reallyStrongPassword')
    adminUser.save()
    result = client.post('/login-api', data={
        'email': 'admin@example.com',
        'password': 'reallyStrongPassword',
    })
    # user with no profile is a failure
    assert result.status_code == 500

def test_login_api_missing_form_values(client):
    ''' Tests login without required form values fails and returns appropriate messaging. '''
    result = client.post('/login-api')
    assert result.status_code == 400
    assert result.data == b'Missing required values email required, password required'

def test_login_api_bad_password(client):
    ''' Tests passwords must match to log in. '''
    testUser = datamodels.User(
        email='gooduser@example.com',
        id=1,
    )
    testUser.set_password('reallyStrongPassword')
    testUser.save()
    result = client.post('/login-api', data={
        'email': 'gooduser@example.com',
        'password': 'badPassword',
    })
    assert result.status_code == 401
    assert result.data == b'User gooduser@example.com not found or invalid password'

def test_login_api_admin_not_connected(client):
    ''' Tests that valid user without valid connection to admin fails and returns appropriate messaging. '''
    testUser = datamodels.User(
        email='gooduser@example.com',
        id=1,
    )
    testUser.set_password('reallyStrongPassword')
    testUser.save()
    adminUser = datamodels.User(
        email='admin@example.com',
        id=2,
        admin=True,
    )
    adminUser.set_password('reallyStrongPassword')
    adminUser.save()
    testProfile = datamodels.Profile(
        display_name='Test User',
        handle='test_handle',
        user_id=1,
    )
    testProfile.save()
    adminProfile = datamodels.Profile(
        display_name='Admin User',
        handle='admin_handle',
        user_id=2,
    )
    adminProfile.save()
    adminConnection = datamodels.Connection(
        profile=adminProfile,
        host='localhost',
        handle='test_handle',
        status=connection_status.PENDING,
    )
    adminConnection.save()
    result = client.post('/login-api', data={
        'email': 'gooduser@example.com',
        'password': 'reallyStrongPassword',
    })
    assert result.status_code == 401
    assert result.data == b'Request to join still pending'

def test_login_api_admin(client):
    ''' Tests that admin login does not require a connection. '''
    adminUser = datamodels.User(
        email='admin@example.com',
        id=2,
        admin=True,
    )
    adminUser.set_password('reallyStrongPassword')
    adminUser.save()
    adminProfile = datamodels.Profile(
        display_name='Admin User',
        handle='admin_handle',
        user_id=2,
    )
    adminProfile.save()
    with mock.patch('socialmedia.views.auth.jwt') as jwt:
        with mock.patch('socialmedia.views.auth.datetime') as dt:
            utcnow_val = datetime(1990, 1, 1, 0, 0)
            dt.utcnow.return_value = utcnow_val
            jwt.encode.return_value = 'token response'
            result = client.post('/login-api', data={
                'email': 'admin@example.com',
                'password': 'reallyStrongPassword',
            })
            assert result.status_code == 200
            assert len(result.json.keys()) == 2
            assert all(h in result.json.keys() for h in (AUTH_HEADER_NAME, 'expires'))
            assert result.json[AUTH_HEADER_NAME] == 'token response'
            assert result.json['expires'] == (utcnow_val + timedelta(hours=6)).timestamp()
            assert session['user'] == adminProfile.as_json()

def test_login_api_no_admin(client):
    ''' Tests that valid user without valid connection to admin fails and returns appropriate messaging. '''
    testUser = datamodels.User(
        email='gooduser@example.com',
        id=1,
    )
    testUser.set_password('reallyStrongPassword')
    testUser.save()
    testProfile = datamodels.Profile(
        display_name='Test User',
        handle='test_handle',
        user_id=1,
    )
    testProfile.save()
    result = client.post('/login-api', data={
        'email': 'gooduser@example.com',
        'password': 'reallyStrongPassword',
    })
    assert result.status_code == 401
    assert result.data == b'Request to join still pending'

