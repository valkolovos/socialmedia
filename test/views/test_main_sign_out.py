from flask import session

from test import datamodels
from .utils import client

def test_sign_out(client):
    # not adding either of these to test.datamodels
    # because an authenticated_user in the session
    # should not need to be retrieved
    admin_user = datamodels.User(
        email='admin@example.com',
        id=2,
        admin=True,
    )
    admin_profile = datamodels.Profile(
        display_name='Admin User',
        handle='admin_handle',
        user_id=2,
    )
    # need to set a user id in the session
    # this will also call socialmedia.views.auth.load_user
    with client.session_transaction() as sess:
        sess['_user_id'] = 2
        sess['authenticated_user'] = admin_user.as_json()
        sess['user'] = admin_profile.as_json()
    response = client.get('/sign-out')
    assert 'user' not in session
    assert 'authenticated_user' not in session
    assert response.status_code == 200


