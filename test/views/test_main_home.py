from flask import session
from test import datamodels
from .utils import client

def test_home_authenticated_user(client):
    # not adding either of these to test.datamodels
    # because an authenticated_user in the session
    # should not need to be retrieved
    admin_user = datamodels.User(
        email='admin@example.com',
        id=datamodels.User.generate_uuid(),
        admin=True,
    )
    admin_profile = datamodels.Profile(
        display_name='Admin User',
        handle='admin_handle',
        user_id=admin_user.id,
    )
    # need to set a user id in the session
    # this will also call socialmedia.views.auth.load_user
    with client.session_transaction() as sess:
        sess['_user_id'] = admin_user.id
        sess['authenticated_user'] = admin_user.as_json()
        sess['user'] = admin_profile.as_json()
    response = client.get('/')
    assert response.status_code == 200

def test_home_not_logged_in(client):
    response = client.get('/')
    assert response.status_code == 302
    assert response.location == 'http://localhost/login?next=%2F'

def test_home_authenticated_user_not_in_session(client):
    # saving these so that they can be retrieved
    # by load_user
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
    response = client.get('/')
    assert response.status_code == 200
    assert session['authenticated_user']['id'] == admin_user.id

def test_home_authenticated_user_doesnt_exist(client):
    admin_user = datamodels.User(
        email='admin@example.com',
        id=datamodels.User.generate_uuid(),
        admin=True,
    )
    # deliberately not saving the user
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
    response = client.get('/')
    # because the user doesn't exist in the database, authentication
    # will fail and the user should be redirected to logini
    assert response.status_code == 302
    assert response.location == 'http://localhost/login?next=%2F'

