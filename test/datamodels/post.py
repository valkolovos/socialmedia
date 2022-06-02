from socialmedia.models import Post as BasePost

from .base import BaseTestModel

class Post(BasePost, BaseTestModel):
    pass
