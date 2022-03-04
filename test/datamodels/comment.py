from socialmedia.models import Comment as BaseComment

from .base import BaseTestModel

class Comment(BaseComment, BaseTestModel):
    pass

