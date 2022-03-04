from socialmedia.models import CommentReference as BaseCommentReference

from .base import BaseTestModel

class CommentReference(BaseCommentReference, BaseTestModel):
    pass

