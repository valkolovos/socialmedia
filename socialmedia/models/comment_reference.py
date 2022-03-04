from datetime import datetime
from dateutil import tz

class CommentReference():

    def __init__(self, **kwargs):
        self.connection = kwargs.get('connection')
        self.message_id = kwargs.get('message_id')
        self.read = kwargs.get('read')
        self.created = kwargs.get('created', datetime.now().astimezone(tz.UTC))

    def __str__(self):
        return f'connection: {{ {str(self.connection)} }}, message_id: {self.message_id}, '\
            f'read: {self.read}, created: {self.created}'

    def __repr__(self):
        return f'CommentReference(connection: {{ {repr(self.connection)} }}, ' \
            f'message_id: {self.message_id}, read: {self.read}, created: {self.created})'

    def __eq__(self, other):
        return all([
            type(other) == type(self),
            hasattr(other, 'connection') and self.connection == other.connection,
            hasattr(other, 'message_id') and self.message_id == other.message_id,
        ])

