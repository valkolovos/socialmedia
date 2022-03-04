import pytest

from flask import session, current_app
from flask_login import current_user

from socialmedia import connection_status

from test import datamodels
from .utils import client

def test_login_post(client):
    ''' Tests a standard login. User must have valid connection with admin user. '''
    testUser = datamodels.User(
        email='gooduser@example.com',
        id=1,
    )
    testUser.set_password('reallyStrongPassword')
    adminUser = datamodels.User(
        email='admin@example.com',
        id=2,
        admin=True,
    )
    adminUser.set_password('reallyStrongPassword')
    testProfile = datamodels.Profile(
        display_name='Test User',
        handle='test_handle',
        user_id=1,
    )
    adminProfile = datamodels.Profile(
        display_name='Admin User',
        handle='admin_handle',
        user_id=2,
    )
    adminConnection = datamodels.Connection(
        profile=adminProfile,
        host='localhost',
        handle='test_handle',
        status=connection_status.CONNECTED,
    )
    datamodels.User.add_data(testUser)
    datamodels.User.add_data(adminUser)
    datamodels.Profile.add_data(testProfile)
    datamodels.Profile.add_data(adminProfile)
    datamodels.Connection.add_data(adminConnection)
    result = client.post('/login', data={
        'email': 'gooduser@example.com',
        'password': 'reallyStrongPassword',
    })
    assert result.status_code == 302
    assert result.location == 'http://localhost/'
    assert session['user'] == testProfile.as_json()
    if hasattr(current_app, 'login_manager'):
        assert current_user.is_authenticated

def test_login_post_no_user(client):
    ''' Tests login with non-existent user fails '''
    result = client.post('/login', data={
        'email': 'notfounduser@example.com',
        'password': 'reallyStrongPassword',
    })
    assert result.status_code == 200
    assert result.location is None
    assert b'Error logging in' in result.data
    assert session.get('user') is None
    if hasattr(current_app, 'login_manager'):
        assert not current_user.is_authenticated

def test_login_post_missing_form_values(client):
    ''' Tests login without required form values fails and returns appropriate messaging. '''
    result = client.post('/login')
    assert result.status_code == 200
    assert result.location is None
    assert b'email required' in result.data
    assert b'password required' in result.data
    assert session.get('user') is None
    if hasattr(current_app, 'login_manager'):
        assert not current_user.is_authenticated

def test_login_post_bad_password(client):
    ''' Tests passwords must match to log in. '''
    testUser = datamodels.User(
        email='gooduser@example.com',
        id=1,
    )
    testUser.set_password('reallyStrongPassword')
    datamodels.User.add_data(testUser)
    result = client.post('/login', data={
        'email': 'gooduser@example.com',
        'password': 'badPassword',
    })
    assert result.status_code == 200
    assert result.location is None
    assert b'Error logging in' in result.data
    assert session.get('user') is None
    if hasattr(current_app, 'login_manager'):
        assert not current_user.is_authenticated

def test_login_post_admin_not_connected(client):
    ''' Tests that valid user without valid connection to admin fails and returns appropriate messaging. '''
    testUser = datamodels.User(
        email='gooduser@example.com',
        id=1,
    )
    testUser.set_password('reallyStrongPassword')
    adminUser = datamodels.User(
        email='admin@example.com',
        id=2,
        admin=True,
    )
    adminUser.set_password('reallyStrongPassword')
    testProfile = datamodels.Profile(
        display_name='Test User',
        handle='test_handle',
        user_id=1,
    )
    adminProfile = datamodels.Profile(
        display_name='Admin User',
        handle='admin_handle',
        user_id=2,
    )
    adminConnection = datamodels.Connection(
        profile=adminProfile,
        host='localhost',
        handle='test_handle',
        status=connection_status.PENDING,
    )
    datamodels.User.add_data(testUser)
    datamodels.User.add_data(adminUser)
    datamodels.Profile.add_data(testProfile)
    datamodels.Profile.add_data(adminProfile)
    datamodels.Connection.add_data(adminConnection)
    result = client.post('/login', data={
        'email': 'gooduser@example.com',
        'password': 'reallyStrongPassword',
    })
    assert result.status_code == 401
    assert result.data == b'Request to join still pending'
    assert session.get('user') is None
    if hasattr(current_app, 'login_manager'):
        assert not current_user.is_authenticated

def test_login_post_admin(client):
    ''' Tests that admin login does not require a connection. '''
    adminUser = datamodels.User(
        email='admin@example.com',
        id=2,
        admin=True,
    )
    adminUser.set_password('reallyStrongPassword')
    adminProfile = datamodels.Profile(
        display_name='Admin User',
        handle='admin_handle',
        user_id=2,
    )
    datamodels.User.add_data(adminUser)
    datamodels.Profile.add_data(adminProfile)
    result = client.post('/login', data={
        'email': 'admin@example.com',
        'password': 'reallyStrongPassword',
    })
    assert result.status_code == 302
    assert result.location == 'http://localhost/'
    assert session['user'] == adminProfile.as_json()
    if hasattr(current_app, 'login_manager'):
        assert current_user.is_authenticated
