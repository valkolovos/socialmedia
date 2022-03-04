from datetime import datetime
from dateutil import tz

class CommentReference():

    def __init__(self, **kwargs):
        self.connection = kwargs.get('connection')
        self.message_id = kwargs.get('message_id')
        self.read = kwargs.get('read')
        self.created = kwargs.get('created', datetime.now().astimezone(tz.UTC))

    def __str__(self):
        connection_handle = self.connection.handle if self.connection else ''
        return f'connection: {connection_handle}, read: {self.read}'

    def __repr__(self):
        connection_handle = self.connection.handle if self.connection else ''
        return f'connection: {connection_handle}, read: {self.read}'

    def __eq__(self, other):
        return all([
            hasattr(other, 'connection') and self.connection == other.connection,
            hasattr(other, 'message_id') and self.object_id == other.object_id,
            hasattr(other, 'read') and self.read == other.read,
            hasattr(other, 'created') and self.created == other.created,
        ])

