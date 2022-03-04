from google.cloud import datastore

from socialmedia.dataclient import datastore_client
from socialmedia.models import Message  as BaseMessage
from socialmedia.datastore.mixins import DatastoreGetMixin, DatastoreBase

class Message(BaseMessage, DatastoreBase, DatastoreGetMixin):
    kind = 'Message'

    def save(self):
        if not hasattr(self,'key'):
            key = datastore_client.key('Message',
                parent=self.profile.key if self.profile else None)
        else:
            key = self.key
        message_entity = datastore.Entity(key=key)
        message_entity.update(self.as_dict())
        datastore_client.put(message_entity)

    def as_dict(self):
        return {
            'id': self.id,
            'text': self.text,
            'files': self.files,
            'created': self.created,
        }


