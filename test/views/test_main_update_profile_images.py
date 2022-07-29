import base64
import json

from unittest.mock import MagicMock

from flask import url_for
from flask_login import AUTH_HEADER_NAME

from test import datamodels
from .utils import client, create_token

def test_update_profile_image(client):
    mock_stream_factory = MagicMock()
    mock_stream = MagicMock()
    mock_stream_factory.return_value = mock_stream
    client.application.stream_factory = mock_stream_factory
    user = datamodels.User(
        email='user@example.com',
        id=datamodels.User.generate_uuid(),
    )
    user.save()
    profile = datamodels.Profile(
        display_name='User',
        handle='handle',
        user_id=user.id,
    )
    profile.save()
    token = create_token(client, user)
    image_bytes = b'image data'
    image_data = base64.b64encode(image_bytes)
    response = client.post(
        url_for('main.update_profile_images'),
        data = {
            'profileImage': f'data:plain/text;base64,{image_data.decode("utf-8")}'
        },
        headers={AUTH_HEADER_NAME: token}
    )
    assert mock_stream.write.called_with(image_bytes)
    assert mock_stream.stop.called
    assert response.status_code == 200
    json_response = json.loads(response.data)
    assert json_response['image'] == client.application.url_signer(
        [f'{profile.user_id}-profile.text']
    )[0]
    profile = datamodels.Profile.get(user_id=user.id)
    assert profile.image == f'{profile.user_id}-profile.text'
    assert 'cover_image' not in json_response
    assert profile.cover_image is None

def test_update_cover_image(client):
    mock_stream_factory = MagicMock()
    mock_stream = MagicMock()
    mock_stream_factory.return_value = mock_stream
    client.application.stream_factory = mock_stream_factory
    user = datamodels.User(
        email='user@example.com',
        id=datamodels.User.generate_uuid(),
    )
    user.save()
    profile = datamodels.Profile(
        display_name='User',
        handle='handle',
        user_id=user.id,
    )
    profile.save()
    token = create_token(client, user)
    image_bytes = b'image data'
    image_data = base64.b64encode(image_bytes)
    response = client.post(
        url_for('main.update_profile_images'),
        data = {
            'coverImage': f'data:plain/text;base64,{image_data.decode("utf-8")}'
        },
        headers={AUTH_HEADER_NAME: token}
    )
    assert mock_stream.write.called_with(image_bytes)
    assert mock_stream.stop.called
    assert response.status_code == 200
    json_response = json.loads(response.data)
    assert json_response['cover_image'] == client.application.url_signer(
        [f'{profile.user_id}-cover.text']
    )[0]
    profile = datamodels.Profile.get(user_id=user.id)
    assert profile.cover_image == f'{profile.user_id}-cover.text'
    assert 'image' not in json_response
    assert profile.image is None

def test_bad_data(client):
    mock_stream_factory = MagicMock()
    mock_stream = MagicMock()
    mock_stream_factory.return_value = mock_stream
    client.application.stream_factory = mock_stream_factory
    user = datamodels.User(
        email='user@example.com',
        id=datamodels.User.generate_uuid(),
    )
    user.save()
    profile = datamodels.Profile(
        display_name='User',
        handle='handle',
        user_id=user.id,
    )
    profile.save()
    token = create_token(client, user)
    response = client.post(
        url_for('main.update_profile_images'),
        data = {
            'coverImage': 'this is definitely bad data'
        },
        headers={AUTH_HEADER_NAME: token}
    )
    assert not mock_stream.write.called
    assert not mock_stream.stop.called
    assert response.status_code == 400
    assert response.data == b'Invalid image data'
