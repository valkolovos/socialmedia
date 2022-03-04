from google.cloud import datastore

from .profile import Profile
from socialmedia.dataclient import datastore_client
from socialmedia.models import Connection as BaseConnection
from socialmedia.datastore.mixins import DatastoreGetMixin, DatastoreBase

class Connection(BaseConnection, DatastoreBase, DatastoreGetMixin):
    kind = 'Connection'

    def save(self):
        if not hasattr(self,'key'):
            key = datastore_client.key('Connection',
                parent=self.profile.key if self.profile else None)
        else:
            key = self.key
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
            key = datastore_client.key('Profile', datastore_obj.key.parent.id)
            datastore_obj = datastore_client.get(key)
            self.profile = Profile._build_obj(datastore_obj)
