from socialmedia.models import Profile as BaseProfile

from .base import BaseTestModel

class Profile(BaseProfile, BaseTestModel):
    pass
