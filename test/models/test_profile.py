import uuid

from Crypto.PublicKey import RSA
from datetime import datetime

from socialmedia.models import Profile

def test_constructor():
    profile = Profile(
        display_name = 'Display Name',
        handle = 'handle',
        user_id = 'user_id'
    )
    assert profile.display_name == 'Display Name'
    assert profile.handle == 'handle'
    assert profile.user_id == 'user_id'
    assert RSA.import_key(profile.public_key)
    assert RSA.import_key(profile.private_key)
    assert type(profile.created) == datetime

def test_str():
    profile = Profile(
        display_name = 'Display Name',
        handle = 'handle',
        user_id = 'user_id',
        image = 'image',
        cover_image = 'cover_image',
    )
    expected_str = f'display_name: {profile.display_name}, handle: {profile.handle}, ' \
        f'user_id: {profile.user_id}, image: {profile.image}, ' \
        f'cover_image: {profile.cover_image}, created: {profile.created}'
    assert str(profile) == expected_str

def test_repr():
    profile = Profile(
        display_name = 'Display Name',
        handle = 'handle',
        user_id = 'user_id',
        image = 'image',
        cover_image = 'cover_image',
    )
    expected_repr =  f'Profile(display_name: {profile.display_name}, handle: {profile.handle}, ' \
        f'user_id: {profile.user_id}, image: {profile.image}, cover_image: {profile.cover_image}, ' \
        f'public_key: {profile.public_key}, created: {profile.created})'
    assert repr(profile) == expected_repr

def test_eq():
    profile_one = Profile(
        display_name = 'Display Name',
        handle = 'handle',
        user_id = 'user_id',
        image = 'image',
        cover_image = 'cover_image',
    )
    profile_two = Profile(
        display_name = 'Display Name',
        handle = 'handle',
        user_id = 'user_id',
        image = 'image',
        cover_image = 'cover_image',
        public_key = profile_one.public_key,
        private_key = profile_one.private_key,
        created = profile_one.created,
    )
    assert profile_one == profile_two

def test_not_eq():
    profile_one = Profile(
        display_name = 'Display Name',
        handle = 'handle',
        user_id = 'user_id'
    )
    profile_two = Profile(
        display_name = 'Display Name',
        handle = 'handle',
        user_id = 'user_id',
    )
    assert profile_one != profile_two

def test_as_json():
    profile = Profile(
        display_name = 'Display Name',
        handle = 'handle',
        user_id = 'user_id'
    )
    assert profile.as_json() == {
        'display_name': profile.display_name,
        'handle': profile.handle,
        'user_id': profile.user_id,
        'public_key': str(profile.public_key),
        'created': str(profile.created),
    }
