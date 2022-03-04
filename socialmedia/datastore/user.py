from google.cloud import datastore

from .dataclient import datastore_client
from socialmedia.models import User as BaseUser
from socialmedia.datastore.mixins import DatastoreGetMixin, DatastoreBase

class User(BaseUser, DatastoreBase, DatastoreGetMixin):

    kind = 'User'

    def save(self):
        if not hasattr(self,'key'):
            key = datastore_client.key('User')
        else:
            key = self.key
        key = datastore_client.key('User')
        user_entity = datastore.Entity(key=key)
        user_entity.update(self.as_dict())
        datastore_client.put(user_entity)

    def as_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'password': self.password,
            'admin': self.admin,
        }
