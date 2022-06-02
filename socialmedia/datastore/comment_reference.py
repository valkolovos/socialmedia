from uuid import uuid4

from google.cloud import datastore

from socialmedia.models import CommentReference as BaseCommentReference
from socialmedia.datastore.mixins import DatastoreBase

from .connection import Connection
from .dataclient import datastore_client

class CommentReference(BaseCommentReference, DatastoreBase):
    kind = 'CommentReference'

    def save(self):
        if not hasattr(self,'key'):
            key = datastore_client.key('CommentReference', str(uuid4()),
                parent=getattr(self.connection, 'key')
                if self.connection and hasattr(self.connection, 'key')
                else None
            )
            setattr(self, 'key', key)
        else:
            key = getattr(self, 'key')
        notification_entity = datastore.Entity(key=key)
        notification_entity.update(self.as_dict())
        datastore_client.put(notification_entity)

    def as_dict(self):
        return {
            'post_id': self.post_id,
            'read': self.read,
            'reference_read': self.reference_read,
            'created': self.created
        }

    def from_datastore_obj(self, datastore_obj):
        if not self.connection:
            datastore_obj = datastore_client.get(self.key.parent)
            self.connection = Connection._build_obj(datastore_obj) # pylint: disable=protected-access
