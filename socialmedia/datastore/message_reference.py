from google.cloud import datastore

from .dataclient import datastore_client
from socialmedia.models import MessageReference as BaseMessageReference
from socialmedia.datastore.mixins import DatastoreGetMixin, DatastoreBase

class MessageReference(BaseMessageReference, DatastoreBase, DatastoreGetMixin):
    kind = 'MessageReference'

    def save(self):
        if not hasattr(self,'key'):
            key = datastore_client.key('MessageReference',
                parent=self.profile.key if self.profile else None)
        else:
            key = self.key
        notification_entity = datastore.Entity(key=key)
        notification_entity.update(self.as_dict())
        datastore_client.put(notification_entity)

    def as_dict(self):
        return {
            'message_id': self.object_id,
            'read': self.read,
            'created': self.created
        }

