from google.cloud import datastore

from .dataclient import datastore_client
from socialmedia.models import Profile as BaseProfile
from socialmedia.datastore.mixins import DatastoreGetMixin, DatastoreBase

class Profile(BaseProfile, DatastoreBase, DatastoreGetMixin):

    kind = 'Profile'

    def save(self):
        if not hasattr(self, 'key'):
            key = datastore_client.key('Profile')
        else:
            key = self.key
        profile_entity = datastore.Entity(
            key=key, exclude_from_indexes=('public_key', 'private_key')
        )
        profile_entity.update(self.as_dict())
        datastore_client.put(profile_entity)
        self.datastore_id = profile_entity.id

    def as_dict(self):
        return {
            'display_name': self.display_name,
            'handle': self.handle,
            'user_id': self.user_id,
            'public_key': self.public_key,
            'private_key': self.private_key,
            'created': self.created,
        }

