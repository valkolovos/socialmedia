from flask import session, url_for

from test import datamodels
from .utils import client

def test_login(client):
    response = client.get(url_for('auth.login'))
    assert response.status_code == 200
    assert len(response.data) > 0

def test_signup(client):
    response = client.get(url_for('auth.signup'))
    assert response.status_code == 200
    assert len(response.data) > 0

def test_logout(client):
    admin_user = datamodels.User(
        email='admin@example.com',
        id=datamodels.User.generate_uuid(),
        admin=True,
    )
    admin_user.save()
    admin_profile = datamodels.Profile(
        display_name='Admin User',
        handle='admin_handle',
        user_id=admin_user.id,
    )
    admin_profile.save()
    # need to set a user id in the session
    # this will also call socialmedia.views.auth.load_user
    with client.session_transaction() as sess:
        sess['_user_id'] = admin_user.id
        sess['user'] = admin_profile.as_json()
    client.get('/')
    response = client.get(url_for('auth.logout'))
    assert response.status_code == 200
    response = client.get('/')
    assert response.status_code == 302
    assert response.location == 'http://localhost/login?next=%2F'
