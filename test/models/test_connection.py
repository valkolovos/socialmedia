import uuid

import pytest

from datetime import datetime

from socialmedia import connection_status
from socialmedia.models import Connection, Profile

def test_constructor():
    connection = Connection(
        profile=Profile(),
        host='abc.xyz',
        handle='conn_handle',
        display_name='Connection Display Name',
        public_key='public_key',
        status=connection_status.PENDING,
    )
    assert uuid.UUID(connection.id)
    assert type(connection.profile) == Profile
    assert connection.host == 'abc.xyz'
    assert connection.handle == 'conn_handle'
    assert connection.public_key == 'public_key'
    assert connection.status == connection_status.PENDING
    assert type(connection.created) == datetime
    assert type(connection.updated) == datetime

def test_constructor_bad_connection():
    with pytest.raises(Exception) as e_info:
        Connection(status='bad')
    assert e_info.exconly() == f'Exception: Connection status must be one of [{", ".join(connection_status.ALL)}]'

def test_str():
    connection = Connection(
        profile=Profile(),
        host='abc.xyz',
        handle='conn_handle',
        display_name='Connection Display Name',
        public_key='public_key',
        status=connection_status.PENDING,
    )
    expected_str = f'id: {connection.id}, profile: {{ {connection.profile} }}, host: {connection.host}, ' \
        f'handle: {connection.handle}, status: {connection.status}, created: {connection.created}, ' \
        f'updated: {connection.updated}'
    assert str(connection) == expected_str

def test_repr():
    connection = Connection(
        profile=Profile(),
        host='abc.xyz',
        handle='conn_handle',
        display_name='Connection Display Name',
        public_key='public_key',
        status=connection_status.PENDING,
    )
    expected_repr = f'Connection(id: {connection.id}, profile: {{ {connection.profile} }}, ' \
        f'host: {connection.host}, handle: {connection.handle}, status: {connection.status}, ' \
        f'public_key: {connection.public_key}, created: {connection.created}, updated: {connection.updated})'
    assert repr(connection) == expected_repr

def test_eq():
    connection_one = Connection(
        profile=Profile(),
        host='abc.xyz',
        handle='conn_handle',
        display_name='Connection Display Name',
        public_key='public_key',
        status=connection_status.PENDING,
    )
    connection_two = Connection(
        id=connection_one.id,
        profile=connection_one.profile,
        host='abc.xyz',
        handle='conn_handle',
        display_name='Connection Display Name',
        public_key='public_key',
        status=connection_status.PENDING,
        created=connection_one.created,
        updated=connection_one.updated,
    )
    assert connection_one == connection_two

def test_not_eq():
    connection_one = Connection(
        profile=Profile(),
        host='abc.xyz',
        handle='conn_handle',
        display_name='Connection Display Name',
        public_key='public_key',
        status=connection_status.PENDING,
    )
    connection_two = Connection(
        id=connection_one.id,
        profile=connection_one.profile,
        host='abc.xyz',
        handle='conn_handle',
        display_name='Connection Display Name is Different',
        public_key='public_key',
        status=connection_status.PENDING,
        created=connection_one.created,
        updated=connection_one.updated,
    )
    assert connection_one != connection_two

def test_as_json():
    connection = Connection(
        profile=Profile(),
        host='abc.xyz',
        handle='conn_handle',
        display_name='Connection Display Name',
        public_key='public_key',
        status=connection_status.PENDING,
    )
    assert connection.as_json() == {
        'id': connection.id,
        'profile': connection.profile.as_json(),
        'host': connection.host,
        'handle': connection.handle,
        'display_name': connection.display_name,
        'status': connection.status,
        'created': connection.created,
        'updated': connection.updated,
    }
