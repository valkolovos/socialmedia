from datetime import datetime
from dateutil import tz
from uuid import uuid4

from socialmedia.models.profile import Profile

class Comment():

    def __init__(self, **kwargs):
        now = datetime.now().astimezone(tz.UTC)
        self.profile = kwargs.get('profile')
        self.id = kwargs.get('id', self.__class__.generate_uuid())
        self.message_id = kwargs.get('message_id')
        self.created = kwargs.get('created', now)
        self.text = kwargs.get('text', '')
        self.files = kwargs.get('files', [])

    def __str__(self):
        return f'id: {self.id}, message_id: {self.message_id}, profile: {{ {str(self.profile)} }}, ' \
                f'text: {self.text}, files: {self.files}, created: {self.created}'

    def __repr__(self):
        return f'Comment(id: {self.id}, message_id: {self.message_id}, profile: {{ {repr(self.profile)} }}, ' \
                f'text: {self.text}, files: {self.files}, created: {self.created})'

    def __eq__(self, other):
        return all([
            hasattr(other, 'profile') and self.profile == other.profile,
            hasattr(other, 'id') and self.id == other.id,
            hasattr(other, 'text') and self.text == other.text,
            hasattr(other, 'message_id') and self.message_id == other.message_id,
            hasattr(other, 'created') and self.created == other.created,
            hasattr(other, 'files') and len(self.files) == len(other.files) and \
                all(self.files[i] == other.files[i] for i in range(len(self.files))),
        ])

    def as_json(self):
        return {
            'profile': self.profile.as_json(),
            'id': self.id,
            'message_id': self.message_id,
            'text': self.text,
            'created': str(self.created),
            'files': self.files,
        }

    @classmethod
    def generate_uuid(cls):
        return str(uuid4())


