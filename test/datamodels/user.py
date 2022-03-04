from socialmedia.models import User as BaseUser

from .base import BaseTestModel

class User(BaseUser, BaseTestModel):
    pass
