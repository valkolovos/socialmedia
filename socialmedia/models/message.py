from datetime import datetime

from dateutil import tz
from sortedcontainers import SortedList

from .uuid_mixin import UuidMixin

class Message(UuidMixin):

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
        return f'id: {self.id}, profile: {{ {self.profile} }}, text: {self.text}, ' \
            f'files: {self.files}, created: {self.created}, has_comments: {len(self.comments) > 0}'

    def __repr__(self):
        return f'Message(id: {self.id}, profile: {{ {self.profile} }}, text: {self.text}, ' \
            f'files: {self.files}, created: {self.created}, comments: {self.comments})'

    def __eq__(self, other):
        # pylint: disable=duplicate-code
        return all([
            isinstance(other, self.__class__),
            hasattr(other, 'profile') and self.profile == other.profile,
            hasattr(other, 'id') and self.id == other.id,
            hasattr(other, 'text') and self.text == other.text,
            hasattr(other, 'created') and self.created == other.created,
            hasattr(other, 'files') and len(self.files) == len(other.files) and
                all(self.files[i] == other.files[i] for i in range(len(self.files))),
        ])

    def as_json(self):
        return {
            'profile': self.profile.as_json(),
            'id': self.id,
            'text': self.text,
            'created': str(self.created),
            'files': self.files,
            'comments': [comment.as_json() for comment in self.comments]
        }
