from datetime import datetime

from dateutil import tz

from socialmedia import connection_status
from .uuid_mixin import UuidMixin

class Connection(UuidMixin):

    def __init__(self, **kwargs):
        now = datetime.now().astimezone(tz.UTC)
        self.id = kwargs.get('id', self.__class__.generate_uuid())
        self.profile = kwargs.get('profile')
        self.host = kwargs.get('host')
        self.handle = kwargs.get('handle')
        self.display_name = kwargs.get('display_name')
        self.public_key = kwargs.get('public_key')
        self.status = kwargs.get('status')
        self.created = kwargs.get('created', now)
        self.updated = kwargs.get('updated', now)
        if self.status not in connection_status.ALL:
            raise Exception(f'Connection status must be one of [{", ".join(connection_status.ALL)}]')

    def __str__(self):
        return f'id: {self.id}, profile: {{ {self.profile} }}, host: {self.host}, handle: {self.handle}, ' \
            f'status: {self.status}, created: {self.created}, updated: {self.updated}'

    def __repr__(self):
        return f'Connection(id: {self.id}, profile: {{ {self.profile} }}, host: {self.host}, ' \
            f'handle: {self.handle}, status: {self.status}, public_key: {self.public_key}, ' \
            f'created: {self.created}, updated: {self.updated})'

    def __eq__(self, other):
        return all([
            isinstance(other, self.__class__),
            hasattr(other, 'id') and self.id == other.id,
            hasattr(other, 'profile') and self.profile == other.profile,
            hasattr(other, 'host') and self.host == other.host,
            hasattr(other, 'handle') and self.handle == other.handle,
            hasattr(other, 'display_name') and self.display_name == other.display_name,
            hasattr(other, 'public_key') and self.public_key == other.public_key,
            hasattr(other, 'status') and self.status == other.status,
            hasattr(other, 'created') and self.created == other.created,
            hasattr(other, 'updated') and self.updated == other.updated,
        ])

    def as_json(self):
        return {
            'id': self.id,
            'profile': self.profile.as_json(),
            'host': self.host,
            'handle': self.handle,
            'display_name': self.display_name,
            'status': self.status,
            'created': self.created,
            'updated': self.updated,
        }
