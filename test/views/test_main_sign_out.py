from flask import session
from flask_login import AUTH_HEADER_NAME

from test import datamodels
from .utils import client, create_token

def test_sign_out(client):
    admin_user = datamodels.User(
        email='admin@example.com',
        id=2,
        admin=True,
    )
    admin_user.save()
    admin_profile = datamodels.Profile(
        display_name='Admin User',
        handle='admin_handle',
        user_id=2,
    )
    admin_profile.save()
    token = create_token(client, admin_user)
    response = client.get('/sign-out', headers={AUTH_HEADER_NAME: token})
    assert 'user' not in session
    assert 'authenticated_user' not in session
    assert response.status_code == 200


