from datetime import datetime
from dateutil import tz

class PostReference():

    def __init__(self, **kwargs):
        self.connection = kwargs.get('connection')
        self.post_id = kwargs.get('post_id')
        self.read = kwargs.get('read')
        self.reference_read = kwargs.get('reference_read')
        self.created = kwargs.get('created', datetime.now().astimezone(tz.UTC))

    def __str__(self):
        return f'connection: {{ {str(self.connection)} }}, post_id: {self.post_id}, '\
            f'read: {self.read}, created: {self.created}'

    def __repr__(self):
        return f'PostReference(connection: {{ {repr(self.connection)} }}, ' \
            f'post_id: {self.post_id}, read: {self.read}, created: {self.created})'

    def __eq__(self, other):
        return all([
            isinstance(other, self.__class__),
            hasattr(other, 'connection') and self.connection == other.connection,
            hasattr(other, 'post_id') and self.post_id == other.post_id,
        ])

    def as_json(self):
        return {
            'connection': self.connection.as_json(),
            'post_id': self.post_id,
            'read': self.read,
            'reference_read': self.reference_read,
            'created': str(self.created),
        }
