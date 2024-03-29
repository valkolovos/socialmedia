from datetime import datetime

from dateutil import tz

from .uuid_mixin import UuidMixin

class Comment(UuidMixin):

    def __init__(self, **kwargs):
        now = datetime.now().astimezone(tz.UTC)
        self.profile = kwargs.get('profile')
        self.id = kwargs.get('id', self.__class__.generate_uuid())
        self.post_id = kwargs.get('post_id')
        self.created = kwargs.get('created', now)
        self.text = kwargs.get('text', '')
        self.files = kwargs.get('files', [])

    def __str__(self):
        return f'id: {self.id}, post_id: {self.post_id}, profile: {{ {str(self.profile)} }}, ' \
                f'text: {self.text}, files: {self.files}, created: {self.created}'

    def __repr__(self):
        return f'Comment(id: {self.id}, post_id: {self.post_id}, profile: {{ {repr(self.profile)} }}, ' \
                f'text: {self.text}, files: {self.files}, created: {self.created})'

    def __eq__(self, other):
        # pylint: disable=duplicate-code
        return all([
            hasattr(other, 'profile') and self.profile == other.profile,
            hasattr(other, 'id') and self.id == other.id,
            hasattr(other, 'text') and self.text == other.text,
            hasattr(other, 'post_id') and self.post_id == other.post_id,
            hasattr(other, 'created') and self.created == other.created,
            hasattr(other, 'files') and len(self.files) == len(other.files) and
                all(self.files[i] == other.files[i] for i in range(len(self.files))),
        ])

    def as_json(self):
        return {
            'profile': self.profile.as_json(),
            'id': self.id,
            'post_id': self.post_id,
            'text': self.text,
            'created': str(self.created),
            'files': self.files,
        }
