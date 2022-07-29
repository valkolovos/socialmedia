from google.cloud import datastore

from socialmedia.models import Profile as BaseProfile
from socialmedia.datastore.mixins import DatastoreBase

from .dataclient import datastore_client

class Profile(BaseProfile, DatastoreBase):

    kind = 'Profile'

    def save(self):
        if not hasattr(self, 'key'):
            key = datastore_client.key('Profile', self.user_id)
            setattr(self, 'key', key)
        else:
            key = getattr(self, 'key')
        profile_entity = datastore.Entity(
            key=key, exclude_from_indexes=('public_key', 'private_key')
        )
        profile_entity.update(self.as_dict())
        datastore_client.put(profile_entity)

    def as_dict(self):
        return {
            'display_name': self.display_name,
            'handle': self.handle,
            'user_id': self.user_id,
            'image': self.image,
            'cover_image': self.cover_image,
            'public_key': self.public_key,
            'private_key': self.private_key,
            'created': self.created,
        }
