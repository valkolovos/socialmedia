import uuid

from socialmedia.models import User

def test_constructor():
    user_id = User.generate_uuid()
    user = User(
        id=user_id,
        email='abc@xyz.com',
    )
    assert uuid.UUID(user.id)
    assert user.id == user_id
    assert user.email == user.email
    assert not user.admin

def test_set_password():
    user = User(
        id=User.generate_uuid(),
        email='abc@xyz.com',
    )
    assert user.password is None
    user.set_password('password')
    assert user.password == User.enc_password('password')
    assert User.enc_password('not the same') != user.password

def test_str():
    user = User(
        id=User.generate_uuid(),
        email='abc@xyz.com',
    )
    expected_str =  f'id: {user.id}, email: {user.email}, admin: {user.admin}'
    assert str(user) == expected_str

def test_repr():
    user = User(
        id=User.generate_uuid(),
        email='abc@xyz.com',
    )
    expected_repr =  f'User(id: {user.id}, email: {user.email}, admin: {user.admin}, ' \
        f'has_password: False)'
    assert repr(user) == expected_repr
    user.set_password('password')
    expected_repr =  f'User(id: {user.id}, email: {user.email}, admin: {user.admin}, ' \
        f'has_password: True)'
    assert repr(user) == expected_repr

def test_eq():
    user_one = User(
        id=User.generate_uuid(),
        email='abc@xyz.com',
    )
    user_two = User(
        id=user_one.id,
        email='abc@xyz.com',
    )
    assert user_one == user_two
    user_one.set_password('password')
    user_two.set_password('password')
    assert user_one == user_two

def test_not_eq():
    user_one = User(
        id=User.generate_uuid(),
        email='abc@xyz.com',
    )
    user_two = User(
        id=user_one.id,
        email='abc@foo.com',
    )
    assert user_one != user_two
    user_two.email = user_one.email
    user_one.admin = True
    assert user_one != user_two
