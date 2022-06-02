from google.cloud import datastore

from socialmedia.models import Post  as BasePost
from socialmedia.datastore.mixins import DatastoreBase

from .dataclient import datastore_client
from .profile import Profile

class Post(BasePost, DatastoreBase):
    kind = 'Post'

    def save(self):
        if not hasattr(self,'key'):
            key = datastore_client.key('Post', self.id,
                parent=getattr(self.profile, 'key')
                if self.profile and hasattr(self.profile, 'key')
                else None
            )
            setattr(self, 'key', key)
        else:
            key = getattr(self, 'key')
        post_entity = datastore.Entity(key=key)
        post_entity.update(self.as_dict())
        datastore_client.put(post_entity)

    def as_dict(self):
        return {
            'id': self.id,
            'text': self.text,
            'files': self.files,
            'created': self.created,
        }

    def from_datastore_obj(self, datastore_obj):
        if not self.profile:
            datastore_obj = datastore_client.get(self.key.parent)
            self.profile = Profile._build_obj(datastore_obj) # pylint: disable=protected-access
