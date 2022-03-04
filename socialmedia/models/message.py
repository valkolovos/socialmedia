from datetime import datetime
from dateutil import tz
from sortedcontainers import SortedList
from uuid import uuid4

from socialmedia.models.profile import Profile

class Message():

    def __init__(self, **kwargs):
        now = datetime.now().astimezone(tz.UTC)
        self.profile = kwargs.get('profile')
        self.id = kwargs.get('id', self.__class__.generate_uuid())
        self.created = kwargs.get('created', now)
        self.text = kwargs.get('text', '')
        self.files = kwargs.get('files', [])
        # allows for a list of comments sorted by created date descending
        # might want to move this out into a mixin for messages instead of having
        # it directly in the base class
        self.comments = SortedList(
            key=lambda x: -(x.created.timestamp())
        )

    def __str__(self):
        profile_name = self.profile.handle if self.profile else ''
        return f'profile: {profile_name}, text: {self.text}, created: {self.created}'

    def __repr__(self):
        profile_name = self.profile.handle if self.profile else ''
        return f'profile: {profile_name}, text: {self.text}, created: {self.created}'

    def __eq__(self, other):
        return all([
            hasattr(other, 'profile') and self.profile == other.profile,
            hasattr(other, 'id') and self.id == other.id
        ])

    def as_json(self):
        return {
            'profile': self.profile.as_json(),
            'id': self.id,
            'text': self.text,
            'created': str(self.created),
            'files': self.files,
        }

    @classmethod
    def generate_uuid(cls):
        return str(uuid4())

