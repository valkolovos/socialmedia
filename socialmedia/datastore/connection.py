from google.cloud import datastore

from socialmedia.models import Connection as BaseConnection
from socialmedia.datastore.mixins import DatastoreBase

from .dataclient import datastore_client
from .profile import Profile

class Connection(BaseConnection, DatastoreBase):
    kind = 'Connection'

    def save(self):
        if not hasattr(self,'key'):
            key = datastore_client.key('Connection', self.id,
                parent=getattr(self.profile, 'key')
                if self.profile and hasattr(self.profile, 'key')
                else None
            )
            setattr(self, 'key', key)
        else:
            key = getattr(self, 'key')
        connection_entity = datastore.Entity(key=key, exclude_from_indexes=('public_key',))
        connection_entity.update(self.as_dict())
        datastore_client.put(connection_entity)

    def as_dict(self):
        return {
            'id': self.id,
            'host': self.host,
            'handle': self.handle,
            'display_name': self.display_name,
            'public_key': self.public_key,
            'status': self.status,
            'created': self.created,
            'updated': self.updated,
        }

    def from_datastore_obj(self, datastore_obj):
        if not self.profile:
            datastore_obj = datastore_client.get(self.key.parent)
            self.profile = Profile._build_obj(datastore_obj) # pylint: disable=protected-access
