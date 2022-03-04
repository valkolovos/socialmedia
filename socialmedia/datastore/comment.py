from google.cloud import datastore

from socialmedia.dataclient import datastore_client
from socialmedia.models import Comment  as BaseComment
from socialmedia.datastore.mixins import DatastoreGetMixin, DatastoreBase

class Comment(BaseComment, DatastoreBase, DatastoreGetMixin):
    kind = 'Comment'

    def save(self):
        if not hasattr(self,'key'):
            key = datastore_client.key('Comment',
                parent=self.profile.key if self.profile else None)
        else:
            key = self.key
        comment_entity = datastore.Entity(key=key)
        comment_entity.update(self.as_dict())
        datastore_client.put(comment_entity)

    def as_dict(self):
        return {
            'id': self.id,
            'message_id': self.message_id,
            'text': self.text,
            'files': self.files,
            'created': self.created,
        }



