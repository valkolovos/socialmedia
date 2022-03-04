from datetime import datetime
from dateutil import tz
from uuid import uuid4

class Connection():

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

    @classmethod
    def generate_uuid(cls):
        return str(uuid4())

    def __str__(self):
        profile_name = self.profile.handle if self.profile else ''
        return f'profile: {profile_name}, host: {self.host}, handle: {self.handle}, status: {self.status}'

    def __repr__(self):
        profile_name = self.profile.handle if self.profile else ''
        return f'profile: {profile_name}, host: {self.host}, handle: {self.handle}, status: {self.status}'

    def __eq__(self, other):
        return all([
            hasattr(other, 'profile') and self.profile == other.profile,
            hasattr(other, 'host') and self.host == other.host,
            hasattr(other, 'handle') and self.handle == other.handle,
            hasattr(other, 'status') and self.status == other.status,
            hasattr(other, 'created') and self.created == other.created,
            hasattr(other, 'updated') and self.updated == other.updated,
        ])

    def as_json(self):
        return {
            'id': self.id,
            'host': self.host,
            'handle': self.handle,
            'display_name': self.display_name,
            'status': self.status,
            'created': self.created,
            'updated': self.updated,
        }
