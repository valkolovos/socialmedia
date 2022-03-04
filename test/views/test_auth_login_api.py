from flask import session

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
    result = client.post('/login-api', data={
        'email': 'gooduser@example.com',
        'password': 'reallyStrongPassword',
    })
    assert result.status_code == 200
    assert result.data == b'User logged in'
    assert session['user'] == testProfile.as_json()

def test_login_api_no_user(client):
    ''' Tests login with non-existent user fails '''
    result = client.post('/login-api', data={
        'email': 'notfounduser@example.com',
        'password': 'reallyStrongPassword',
    })
    assert result.status_code == 401
    assert result.data == b'User notfounduser@example.com not found or invalid password'

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
    datamodels.User.add_data(testUser)
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
    adminProfile = datamodels.Profile(
        display_name='Admin User',
        handle='admin_handle',
        user_id=2,
    )
    datamodels.User.add_data(adminUser)
    datamodels.Profile.add_data(adminProfile)
    result = client.post('/login-api', data={
        'email': 'admin@example.com',
        'password': 'reallyStrongPassword',
    })
    assert result.status_code == 200
    assert result.data == b'User logged in'
    assert session['user'] == adminProfile.as_json()

