from socialmedia.models import PostReference as BasePostReference

from .base import BaseTestModel

class PostReference(BasePostReference, BaseTestModel):
    pass

